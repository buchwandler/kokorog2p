"""Markdown annotation support for kokorog2p.

This module provides preprocessing for markdown-style phoneme annotations
compatible with the misaki library format: [word](/phonemes/)

Example:
    >>> from kokorog2p.markdown import preprocess_markdown
    >>> from kokorog2p import get_g2p, phonemize_with_markdown
    >>> text = '[Misaki](/misˈɑki/) is a G2P engine.'
    >>> phonemize_with_markdown(text, 'en-us')
    'misˈɑki ɪz ɐ ʤˈi tˈu pˈi ˈɛnʤən.'
"""

import re
from typing import TYPE_CHECKING

from kokorog2p.token import GToken

if TYPE_CHECKING:
    pass


# Regex pattern for markdown annotations: [word](/phonemes/)
LINK_REGEX = re.compile(r"\[([^\]]+)\]\(([^\)]*)\)")


def preprocess_markdown(text: str) -> tuple[str, list[str], dict[int, str]]:
    """Preprocess text with markdown phoneme annotations.

    Extracts annotations in the format [word](/phonemes/) and returns
    cleaned text along with feature mappings.

    Args:
        text: Text with optional markdown annotations

    Returns:
        Tuple of (cleaned_text, tokens, features) where:
        - cleaned_text: Text with annotations removed (words only)
        - tokens: List of tokens (words)
        - features: Dict mapping token indices to phoneme strings

    Example:
        >>> text = '[Misaki](/misˈɑki/) is great.'
        >>> clean, tokens, features = preprocess_markdown(text)
        >>> clean
        'Misaki is great.'
        >>> features
        {0: 'misˈɑki'}
    """
    result = ""
    tokens = []
    features = {}
    last_end = 0
    text = text.lstrip()

    for m in LINK_REGEX.finditer(text):
        # Add text before this annotation
        result += text[last_end : m.start()]
        tokens.extend(text[last_end : m.start()].split())

        # Extract phonemes (group 2)
        phonemes = m.group(2)

        # Check if it's a phoneme annotation (starts with /)
        if phonemes and phonemes.startswith("/"):
            phonemes = phonemes.strip("/")  # Remove leading and trailing slashes
            features[len(tokens)] = phonemes

        # Add the word (group 1) to result
        result += m.group(1)
        tokens.append(m.group(1))
        last_end = m.end()

    # Add remaining text
    if last_end < len(text):
        result += text[last_end:]
        tokens.extend(text[last_end:].split())

    return result, tokens, features


def apply_markdown_features(
    tokens: list[GToken], features: dict[int, str], original_tokens: list[str]
) -> list[GToken]:
    """Apply phoneme features from markdown annotations to tokens.

    Args:
        tokens: List of GToken objects from G2P
        features: Dict mapping token indices to phoneme strings
        original_tokens: List of original token strings for alignment

    Returns:
        Modified list of GToken objects with features applied
    """
    if not features:
        return tokens

    # Simple alignment: match by token text
    # This assumes G2P tokenization preserves words from preprocessing
    token_map: dict[int, int] = {}
    for i, orig_word in enumerate(original_tokens):
        for j, token in enumerate(tokens):
            if token.text == orig_word and j not in token_map.values():
                token_map[i] = j
                break

    # Apply phoneme features
    for orig_idx, phonemes in features.items():
        if orig_idx in token_map:
            token_idx = token_map[orig_idx]
            tokens[token_idx].phonemes = phonemes
            tokens[token_idx].set("rating", 5)  # Highest rating for user-provided

    return tokens


def phonemize_with_markdown(text: str, language: str = "en-us") -> str:
    """Phonemize text with markdown phoneme annotations.

    Text with [word](/phonemes/) will use the provided phonemes.
    Other text will be phonemized normally.

    This function is compatible with misaki's markdown annotation format.

    Args:
        text: Text with optional markdown phoneme annotations
        language: Language code for G2P (default: 'en-us')

    Returns:
        Phonemized string with annotations applied

    Example:
        >>> text = '[Misaki](/misˈɑki/) is a G2P engine for [Kokoro](/kˈOkəɹO/).'
        >>> phonemize_with_markdown(text)
        'misˈɑki ɪz ɐ ʤˈi tˈu pˈi ˈɛnʤən fɔɹ kˈOkəɹO.'
    """
    # Preprocess markdown annotations
    clean_text, orig_tokens, features = preprocess_markdown(text)

    # Import here to avoid circular imports
    from kokorog2p import get_g2p

    # Phonemize the cleaned text
    g2p = get_g2p(language)
    tokens = g2p(clean_text)

    # Apply markdown features
    tokens = apply_markdown_features(tokens, features, orig_tokens)

    # Join phonemes
    return " ".join(t.phonemes or "" for t in tokens if t.phonemes)


def remove_markdown(text: str) -> str:
    """Remove markdown phoneme annotations, keeping only words.

    Args:
        text: Text with markdown annotations

    Returns:
        Text with annotations removed

    Example:
        >>> remove_markdown('[Misaki](/misˈɑki/) is great.')
        'Misaki is great.'
    """
    return re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", text)


__all__ = [
    "LINK_REGEX",
    "preprocess_markdown",
    "apply_markdown_features",
    "phonemize_with_markdown",
    "remove_markdown",
]
