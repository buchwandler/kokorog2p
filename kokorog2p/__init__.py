"""kokorog2p - Unified G2P (Grapheme-to-Phoneme) library for Kokoro TTS.

This library provides grapheme-to-phoneme conversion for text-to-speech
applications, supporting multiple languages including English, German, French,
Czech, Chinese, Japanese, Korean, and Hebrew.

Supported Languages:
    - English (US/GB): 100k+ dictionary, POS tagging, stress assignment
    - German: 738k+ dictionary, phonological rules, number handling
    - French: Gold dictionary, liaison rules, espeak fallback
    - Czech: Rule-based phonology
    - Chinese: pypinyin with tone sandhi
    - Japanese: pyopenjtalk with mora-based phonemes
    - Korean: MeCab-based phonological rules
    - Hebrew: phonikud-based phonemization (requires nikud)

Example:
    >>> from kokorog2p import phonemize, get_g2p
    >>> # English
    >>> phonemize("Hello world!", language="en-us")
    'hˈɛlO wˈɜɹld!'
    >>> # German
    >>> phonemize("Guten Tag!", language="de")
    'ɡuːtn̩ taːk!'
    >>> # French
    >>> phonemize("Bonjour!", language="fr")
    'bɔ̃ʒuʁ!'
    >>> # Korean
    >>> phonemize("안녕하세요", language="ko")
    >>> # Full control with tokens
    >>> g2p = get_g2p("de")
    >>> tokens = g2p("Das Wetter ist schön.")
    >>> for token in tokens:
    ...     print(f"{token.text} -> {token.phonemes}")
"""

from collections.abc import Callable
from typing import Any, Literal, Optional, Union

from kokorog2p.base import G2PBase

# SSMD annotation support
from kokorog2p.ssmd import (
    ANNOTATION_REGEX,
    ATTR_REGEX,
    apply_ssmd_features,
    phonemize_with_ssmd,
    preprocess_ssmd,
    remove_ssmd,
)
from kokorog2p.multilang import preprocess_multilang
from kokorog2p.speechmarkdown import (
    SPEECHMARKDOWN_ATTR_REGEX,
    SPEECHMARKDOWN_REGEX,
    phonemize_with_speechmarkdown,
    process_speechmarkdown,
    remove_speechmarkdown,
)
from kokorog2p.phonemes import (
    CONSONANTS,
    GB_VOCAB,
    US_VOCAB,
    VOWELS,
    from_espeak,
    from_goruut,
    get_vocab,
    to_espeak,
    validate_phonemes,
)

# Punctuation handling
from kokorog2p.punctuation import (
    KOKORO_PUNCTUATION,
    Punctuation,
    filter_punctuation,
    is_kokoro_punctuation,
    normalize_punctuation,
)

# Core classes
from kokorog2p.token import GToken

# Vocabulary encoding/decoding for Kokoro model
from kokorog2p.vocab import N_TOKENS, PAD_IDX, decode, encode, filter_for_kokoro
from kokorog2p.vocab import get_config as get_kokoro_config
from kokorog2p.vocab import get_vocab as get_kokoro_vocab
from kokorog2p.vocab import ids_to_phonemes, phonemes_to_ids, validate_for_kokoro

# Word mismatch detection
from kokorog2p.words_mismatch import (
    MismatchInfo,
    MismatchMode,
    MismatchStats,
    check_word_alignment,
    count_words,
    detect_mismatches,
)

# Version info
try:
    from kokorog2p._version import __version__, __version_tuple__
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)

# Lazy imports for optional dependencies
_g2p_cache: dict[str, G2PBase] = {}

# Backend type hint
BackendType = Literal["kokorog2p", "espeak", "goruut"]


class SSMDG2P(G2PBase):
    """G2P wrapper that enables SSMD phoneme annotations."""

    def __init__(self, g2p: G2PBase, g2p_factory: Callable[[str], G2PBase]) -> None:
        super().__init__(
            language=g2p.language,
            use_espeak_fallback=g2p.use_espeak_fallback,
            use_goruut_fallback=g2p.use_goruut_fallback,
            strict=g2p.strict,
        )
        self._g2p = g2p
        self._g2p_factory = g2p_factory

    def __call__(self, text: str) -> list[GToken]:
        return self._g2p(text)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        return self._g2p.lookup(word, tag=tag)

    def phonemize(self, text: str) -> str:
        return phonemize_with_ssmd(
            text,
            language=self.language,
            g2p=self._g2p,
            g2p_factory=self._g2p_factory,
        )


class SpeechMarkdownG2P(G2PBase):
    """G2P wrapper that enables SpeechMarkdown annotations."""

    def __init__(self, g2p: G2PBase, g2p_factory: Callable[[str], G2PBase]) -> None:
        super().__init__(
            language=g2p.language,
            use_espeak_fallback=g2p.use_espeak_fallback,
            use_goruut_fallback=g2p.use_goruut_fallback,
            strict=g2p.strict,
        )
        self._g2p = g2p
        self._g2p_factory = g2p_factory

    def __call__(self, text: str) -> list[GToken]:
        return self._g2p(text)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        return self._g2p.lookup(word, tag=tag)

    def phonemize(self, text: str) -> str:
        return phonemize_with_speechmarkdown(
            text,
            language=self.language,
            g2p=self._g2p,
            g2p_factory=self._g2p_factory,
        )


def get_g2p(
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_goruut_fallback: bool = False,
    use_spacy: bool = True,
    backend: BackendType = "kokorog2p",
    load_silver: bool = True,
    load_gold: bool = True,
    version: str = "1.0",
    phoneme_quotes: str = "curly",
    markdown_syntax: Literal["ssmd", "speechmarkdown", "disabled"] = "disabled",
    strict: bool = True,
    **kwargs: Any,
) -> G2PBase:
    """Get a G2P instance for the specified language.

    This factory function returns an appropriate G2P instance based on the
    language code. Results are cached for efficiency. For mixed-language text,
    use preprocess_multilang before SSMD phonemization.

    Args:
        language: Language code (e.g., 'en-us', 'en-gb', 'zh', 'ja', 'fr', etc.).
        use_espeak_fallback: Whether to use espeak for out-of-vocabulary words
            (only applies when backend="espeak").
        use_goruut_fallback: Whether to use goruut for out-of-vocabulary words
            (only applies when backend="espeak").
        use_spacy: Whether to use spaCy for tokenization and POS tagging
            (only applies to English).
        backend: Phonemization backend to use: "kokorog2p", "espeak", "goruut".
            The goruut backend requires pygoruut to be installed.
        load_silver: If True, load silver tier dictionary (~100k extra entries).
            Defaults to True for backward compatibility and maximum coverage.
            Set to False to save memory (~22-31 MB) and initialization time.
            Only applies to English (en-us, en-gb). Other languages reserve
            this parameter for future use.
        load_gold: If True, load gold tier dictionary (~170k common words).
            Defaults to True for maximum quality and coverage.
            Set to False when only silver tier or no dictionaries needed.
            Only applies to languages with dictionaries (English, French, German).
        version: Model version to use. Default: "1.0" (base model).
            - "1.0": Base model
            - "1.1": Chinese/English model
            Different languages may have different behavior:
            - Chinese: "1.0" = IPA output, "1.1" = Zhuyin output
        phoneme_quotes: Quote character style in phoneme output. Options:
            - "curly": Use curly quotes (", ") - default, backward compatible
            - "ascii": Use ASCII double quotes (")
            - "none": Remove quote characters from phoneme output
            Only applies to English currently.
        markdown_syntax: If "ssmd", return a wrapper whose phonemize() understands
            SSMD annotations like [word]{ph="..."} and [word]{lang="..."}.
            If "speechmarkdown", return a wrapper whose phonemize() understands
            SpeechMarkdown annotations like (word)[ipa:"..."] or (word)[lang:"...].
            If "disabled", return a standard G2P instance without special handling.
        strict: If True (default), raise exceptions when backend initialization
            or phonemization fails. If False, log errors and return empty results
            for backward compatibility with older versions that silently failed.
            Recommended: True for production use to catch configuration issues.
        **kwargs: Additional arguments passed to the G2P constructor.

    Returns:
        A G2PBase instance for the specified language.

    Raises:
        ValueError: If the language is not supported and no fallback is available,
            or if version is not "1.0" or "1.1".
        ImportError: If backend="goruut" but pygoruut is not installed.

    Example:
        >>> g2p = get_g2p("en-us")
        >>> tokens = g2p("Hello world!")
        >>> # Disable silver for better performance
        >>> g2p_fast = get_g2p("en-us", load_silver=False)
        >>> # Ultra-fast initialization with no dictionaries
        >>> g2p_minimal = get_g2p("en-us", load_silver=False, load_gold=False)
        >>> # Chinese
        >>> g2p_zh = get_g2p("zh")
        >>> # Japanese
        >>> g2p_ja = get_g2p("ja")
        >>> # French (uses espeak fallback)
        >>> g2p_fr = get_g2p("fr")
        >>> # Using goruut backend
        >>> g2p_goruut = get_g2p("en-us", backend="goruut")
    """
    # Normalize language code
    lang = language.lower().replace("_", "-")

    # Validate version parameter
    if version not in ("1.0", "1.1"):
        raise ValueError(
            f"Invalid version '{version}'. "
            "Must be '1.0' (multilngual) or '1.1' (chinese)."
        )

    # Check cache (include all relevant parameters in cache key)
    cache_key = (
        f"{lang}:{use_espeak_fallback}:{use_goruut_fallback}:{use_spacy}:{backend}:{load_silver}:{load_gold}"
        f":{version}:{phoneme_quotes}:{markdown_syntax}:{strict}"
    )
    if cache_key in _g2p_cache:
        return _g2p_cache[cache_key]

    # Create G2P instance based on language and backend
    g2p: G2PBase

    if backend == "goruut":
        # Use goruut backend for all languages
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P(language=language, strict=strict, version=version, **kwargs)
    elif backend == "espeak":
        # Use espeak backend for all languages
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language=language, strict=strict, version=version, **kwargs)

    elif lang.startswith("en"):
        from kokorog2p.en import EnglishG2P

        g2p = EnglishG2P(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_spacy=use_spacy,
            load_silver=load_silver,
            load_gold=load_gold,
            strict=strict,
            version=version,
            phoneme_quotes=phoneme_quotes,
            **kwargs,
        )
    elif lang in ("zh", "zh-cn", "zh-tw", "cmn", "chinese"):
        from kokorog2p.zh import ChineseG2P

        g2p = ChineseG2P(
            language=language,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("ja", "ja-jp", "jpn", "japanese"):
        from kokorog2p.ja import JapaneseG2P

        g2p = JapaneseG2P(
            language=language,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("fr", "fr-fr", "fra", "french"):
        from kokorog2p.fr import FrenchG2P

        g2p = FrenchG2P(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("cs", "cs-cz", "ces", "czech"):
        from kokorog2p.cs import CzechG2P

        g2p = CzechG2P(
            language=language,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("de", "de-de", "de-at", "de-ch", "deu", "german"):
        from kokorog2p.de import GermanG2P

        g2p = GermanG2P(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("ko", "ko-kr", "kor", "korean"):
        from kokorog2p.ko import KoreanG2P

        g2p = KoreanG2P(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("he", "he-il", "heb", "hebrew"):
        from kokorog2p.he import HebrewG2P

        g2p = HebrewG2P(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    else:
        raise ValueError(
            f"Unsupported language '{language}' for kokorog2p backend. "
            "Use 'espeak' or 'goruut' backend for more languages."
        )

    if markdown_syntax != "disabled:":

        def g2p_factory(override_language: str) -> G2PBase:
            return get_g2p(
                language=override_language,
                use_espeak_fallback=use_espeak_fallback,
                use_goruut_fallback=use_goruut_fallback,
                use_spacy=use_spacy,
                backend=backend,
                load_silver=load_silver,
                load_gold=load_gold,
                version=version,
                phoneme_quotes=phoneme_quotes,
                markdown_syntax="disabled",
                strict=strict,
                **kwargs,
            )

        if markdown_syntax == "speechmarkdown":
            g2p = SpeechMarkdownG2P(g2p, g2p_factory)
        elif markdown_syntax == "ssmd":
            g2p = SSMDG2P(g2p, g2p_factory)

    _g2p_cache[cache_key] = g2p
    return g2p


def phonemize(
    text: str,
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_goruut_fallback: bool = False,
    use_spacy: bool = True,
    backend: BackendType = "kokorog2p",
) -> str:
    """Convert text to phonemes.

    This is a convenience function that creates a G2P instance and converts
    the text to a phoneme string.

    Args:
        text: Input text to convert.
        language: Language code (e.g., 'en-us', 'en-gb').
        use_espeak_fallback: Whether to use espeak for out-of-vocabulary words
            (only applies when backend="espeak").
        use_goruut_fallback: Whether to use goruut for out-of-vocabulary words
            (only applies when backend="goruut").
        use_spacy: Whether to use spaCy for tokenization and POS tagging
            (only applies to English with espeak backend).
        backend: Phonemization backend to use: "kokorog2p", "espeak", "goruut".
            The goruut backend requires pygoruut to be installed.

    Returns:
        Phoneme string.

    Example:
        >>> phonemize("Hello world!")
        'hˈɛlO wˈɜɹld!'
        >>> # Using goruut backend
        >>> phonemize("Hello world!", backend="goruut")
        'həlˈO wˈɜɹld'
    """
    g2p = get_g2p(
        language=language,
        use_espeak_fallback=use_espeak_fallback,
        use_goruut_fallback=use_goruut_fallback,
        use_spacy=use_spacy,
        backend=backend,
    )
    return g2p.phonemize(text)


def tokenize(
    text: str,
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_goruut_fallback: bool = False,
    use_spacy: bool = True,
    backend: BackendType = "kokorog2p",
) -> list[GToken]:
    """Convert text to a list of tokens with phonemes.

    Args:
        text: Input text to convert.
        language: Language code (e.g., 'en-us', 'en-gb').
        use_espeak_fallback: Whether to use espeak for out-of-vocabulary words
            (only applies when backend="espeak").
        use_goruut_fallback: Whether to use goruut for out-of-vocabulary words
            (only applies when backend="goruut").
        use_spacy: Whether to use spaCy for tokenization and POS tagging
            (only applies to English with espeak backend).
        backend: Phonemization backend: "kokorog2p", "espeak", "goruut".
            The goruut backend requires pygoruut to be installed.

    Returns:
        List of GToken objects with phonemes assigned.

    Example:
        >>> tokens = tokenize("Hello world!")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """
    g2p = get_g2p(
        language=language,
        use_espeak_fallback=use_espeak_fallback,
        use_goruut_fallback=use_goruut_fallback,
        use_spacy=use_spacy,
        backend=backend,
    )
    return g2p(text)


def clear_cache() -> None:
    """Clear the G2P instance cache.

    This can be useful when you need to free memory or reset state.
    """
    _g2p_cache.clear()


# Public API
__all__ = [
    # Version
    "__version__",
    "__version_tuple__",
    # Core classes
    "GToken",
    "G2PBase",
    # Main functions
    "phonemize",
    "tokenize",
    "get_g2p",
    "clear_cache",
    # Phoneme utilities
    "US_VOCAB",
    "GB_VOCAB",
    "VOWELS",
    "CONSONANTS",
    "from_espeak",
    "from_goruut",
    "to_espeak",
    "validate_phonemes",
    "get_vocab",
    # Kokoro vocabulary encoding
    "encode",
    "decode",
    "phonemes_to_ids",
    "ids_to_phonemes",
    "validate_for_kokoro",
    "filter_for_kokoro",
    "get_kokoro_vocab",
    "get_kokoro_config",
    "N_TOKENS",
    "PAD_IDX",
    # Punctuation handling
    "Punctuation",
    "normalize_punctuation",
    "filter_punctuation",
    "is_kokoro_punctuation",
    "KOKORO_PUNCTUATION",
    # Word mismatch detection
    "MismatchMode",
    "MismatchInfo",
    "MismatchStats",
    "detect_mismatches",
    "check_word_alignment",
    "count_words",
    # SSMD annotation support
    "phonemize_with_ssmd",
    "preprocess_ssmd",
    "apply_ssmd_features",
    "remove_ssmd",
    "preprocess_multilang",
    "SPEECHMARKDOWN_REGEX",
    "SPEECHMARKDOWN_ATTR_REGEX",
    "process_speechmarkdown",
    "phonemize_with_speechmarkdown",
    "remove_speechmarkdown",
    "ANNOTATION_REGEX",
    "ATTR_REGEX",
]
