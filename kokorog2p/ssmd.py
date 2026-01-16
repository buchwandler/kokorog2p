"""Speech Synthesis Markdown (SSMD) annotation support for kokorog2p.

This module provides preprocessing for SSMD-style annotations
compatible with the SSMD specification: [word]{ph="phonemes"}

Example:
    >>> from kokorog2p.ssmd import preprocess_ssmd
    >>> from kokorog2p import get_g2p, phonemize_with_ssmd
    >>> text = '[Misaki]{ph="misˈɑki"} is a G2P engine. [french]{lang="fr"}'
    >>> phonemize_with_ssmd(text, 'en-us')
    'misˈɑki ɪz ɐ ʤˈi tˈu pˈi ˈɛnʤən.'
"""

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Optional

from kokorog2p.token import GToken

if TYPE_CHECKING:
    from kokorog2p.base import G2PBase


# Regex pattern for SSMD annotations: [word]{ph="phonemes" lang="en"}
ANNOTATION_REGEX = re.compile(r"\[([^\]]+)\]\{([^}]*)\}")
ATTR_REGEX = re.compile(r"(\w+)\s*=\s*\"([^\"]*)\"")


def preprocess_ssmd(
    text: str,
) -> tuple[str, list[str], dict[int, str], dict[int, str]]:
    """Preprocess text with SSMD phoneme annotations.

    Extracts annotations in the format [word]{ph="phonemes" lang="en"}
    and returns cleaned text along with feature mappings.

    Args:
        text: Text with optional SSMD annotations

    Returns:
        Tuple of (cleaned_text, tokens, phoneme_features, language_features) where:
        - cleaned_text: Text with annotations removed (words only)
        - tokens: List of tokens (words)
        - phoneme_features: Dict mapping token indices to phoneme strings
        - language_features: Dict mapping token indices to language codes

    Example:
        >>> text = '[Misaki]{ph="misˈɑki"} is [great]{lang="en-gb"}.'
        >>> clean, tokens, phonemes, languages = preprocess_ssmd(text)
        >>> clean
        'Misaki is great.'
        >>> phonemes
        {0: 'misˈɑki'}
        >>> languages
        {2: 'en-gb'}
    """
    result = ""
    tokens = []
    phoneme_features: dict[int, str] = {}
    language_features: dict[int, str] = {}
    last_end = 0
    text = text.lstrip()

    for m in ANNOTATION_REGEX.finditer(text):
        # Add text before this annotation
        result += text[last_end : m.start()]
        tokens.extend(text[last_end : m.start()].split())

        attrs = {key.casefold(): value for key, value in ATTR_REGEX.findall(m.group(2))}

        if "ph" in attrs:
            phoneme_features[len(tokens)] = attrs["ph"]

        if "lang" in attrs:
            language_features[len(tokens)] = attrs["lang"]

        # Add the word (group 1) to result
        result += m.group(1)
        tokens.append(m.group(1))
        last_end = m.end()

    # Add remaining text
    if last_end < len(text):
        result += text[last_end:]
        tokens.extend(text[last_end:].split())

    return result, tokens, phoneme_features, language_features


def align_ssmd_tokens(
    original_tokens: list[str], tokens: list[GToken]
) -> dict[int, int]:
    """Align original tokens to G2P tokens by word text."""
    token_map: dict[int, int] = {}
    for i, orig_word in enumerate(original_tokens):
        orig_key = orig_word.casefold()
        for j, token in enumerate(tokens):
            if token.text.casefold() == orig_key and j not in token_map.values():
                token_map[i] = j
                break

    return token_map


def apply_ssmd_features(
    tokens: list[GToken], features: dict[int, str], original_tokens: list[str]
) -> list[GToken]:
    """Apply phoneme features from SSMD annotations to tokens.

    Args:
        tokens: List of GToken objects from G2P
        features: Dict mapping token indices to phoneme strings
        original_tokens: List of original token strings for alignment

    Returns:
        Modified list of GToken objects with features applied
    """
    if not features:
        return tokens

    token_map = align_ssmd_tokens(original_tokens, tokens)

    # Apply phoneme features
    for orig_idx, phonemes in features.items():
        if orig_idx in token_map:
            token_idx = token_map[orig_idx]
            tokens[token_idx].phonemes = phonemes
            tokens[token_idx].set("rating", 5)  # Highest rating for user-provided

    return tokens


def phonemize_with_ssmd(
    text: str,
    language: str = "en-us",
    g2p: Optional["G2PBase"] = None,
    g2p_factory: Callable[[str], "G2PBase"] | None = None,
) -> str:
    """Phonemize text with SSMD phoneme annotations.

    Text with [word]{ph="phonemes"} will use the provided phonemes.
    Text with [word]{lang="en"} will be phonemized in the specified language.

    This function is compatible with the SSMD annotation format.

    Args:
        text: Text with optional SSMD phoneme annotations
        language: Language code for G2P (default: 'en-us')
        g2p: Optional G2P instance to reuse
        g2p_factory: Optional factory for language overrides

    Returns:
        Phonemized string with annotations applied

    Example:
        >>> text = '[Misaki]{ph="misˈɑki"} is a G2P engine for [Kokoro]{ph="kˈOkəɹO"}.'
        >>> phonemize_with_ssmd(text)
        'misˈɑki ɪz ɐ ʤˈi tˈu pˈi ˈɛnʤən fɔɹ kˈOkəɹO.'
    """
    # Preprocess SSMD annotations
    clean_text, orig_tokens, phoneme_features, language_features = preprocess_ssmd(text)

    # Import here to avoid circular imports
    from kokorog2p import get_g2p

    # Phonemize the cleaned text
    if g2p is None:
        g2p = get_g2p(language)
    if g2p_factory is None:
        g2p_factory = get_g2p
    tokens = g2p(clean_text)

    if language_features:
        token_map = align_ssmd_tokens(orig_tokens, tokens)
        g2p_cache: dict[str, G2PBase] = {}

        for orig_idx, override_language in language_features.items():
            if orig_idx not in token_map:
                continue

            token_idx = token_map[orig_idx]
            token_text = orig_tokens[orig_idx]
            if not token_text.strip():
                continue

            if override_language not in g2p_cache:
                g2p_cache[override_language] = g2p_factory(override_language)

            override_g2p = g2p_cache[override_language]
            override_tokens = override_g2p(token_text)
            override_phonemes = None
            for override_token in override_tokens:
                if override_token.text.casefold() == token_text.casefold():
                    override_phonemes = override_token.phonemes
                    break

            if override_phonemes is None:
                override_phonemes = " ".join(
                    t.phonemes or "" for t in override_tokens if t.phonemes
                )

            tokens[token_idx].phonemes = override_phonemes

    # Apply SSMD features
    tokens = apply_ssmd_features(tokens, phoneme_features, orig_tokens)

    # Join phonemes
    return " ".join(t.phonemes or "" for t in tokens if t.phonemes)


def remove_ssmd(text: str) -> str:
    """Remove SSMD phoneme annotations, keeping only words.

    Args:
        text: Text with SSMD annotations

    Returns:
        Text with annotations removed

    Example:
        >>> remove_ssmd('[Misaki]{ph="misˈɑki"} is great.')
        'Misaki is great.'
    """
    text = re.sub(r"\[([^\]]+)\]\{[^}]*\}", r"\1", text)
    return re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)


__all__ = [
    "ANNOTATION_REGEX",
    "ATTR_REGEX",
    "preprocess_ssmd",
    "apply_ssmd_features",
    "phonemize_with_ssmd",
    "remove_ssmd",
]
