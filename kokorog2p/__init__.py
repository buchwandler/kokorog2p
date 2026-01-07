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

from typing import Any, Literal, Optional, Union

# Core classes
from kokorog2p.token import GToken
from kokorog2p.base import G2PBase
from kokorog2p.phonemes import (
    US_VOCAB,
    GB_VOCAB,
    from_espeak,
    from_goruut,
    to_espeak,
    validate_phonemes,
    get_vocab,
    VOWELS,
    CONSONANTS,
)

# Vocabulary encoding/decoding for Kokoro model
from kokorog2p.vocab import (
    encode,
    decode,
    phonemes_to_ids,
    ids_to_phonemes,
    validate_for_kokoro,
    filter_for_kokoro,
    get_vocab as get_kokoro_vocab,
    get_config as get_kokoro_config,
    N_TOKENS,
    PAD_IDX,
)

# Punctuation handling
from kokorog2p.punctuation import (
    Punctuation,
    normalize_punctuation,
    filter_punctuation,
    is_kokoro_punctuation,
    KOKORO_PUNCTUATION,
)

# Word mismatch detection
from kokorog2p.words_mismatch import (
    MismatchMode,
    MismatchInfo,
    MismatchStats,
    detect_mismatches,
    check_word_alignment,
    count_words,
)

# Markdown annotation support
from kokorog2p.markdown import (
    phonemize_with_markdown,
    preprocess_markdown,
    apply_markdown_features,
    remove_markdown,
    LINK_REGEX,
)

# Version info
try:
    from kokorog2p._version import __version__, __version_tuple__
except ImportError:
    __version__ = "0.0.0"
    __version_tuple__ = (0, 0, 0)

# Lazy imports for optional dependencies
_g2p_cache: dict[str, G2PBase] = {}

# Import MixedLanguageG2P for type checking
try:
    from kokorog2p.mixed_language_g2p import MixedLanguageG2P
except ImportError:
    MixedLanguageG2P = None  # type: ignore

# Backend type hint
BackendType = Literal["espeak", "goruut"]


def get_g2p(
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_spacy: bool = True,
    backend: BackendType = "espeak",
    load_silver: bool = True,
    load_gold: bool = True,
    multilingual_mode: bool = False,
    allowed_languages: list[str] | None = None,
    language_confidence_threshold: float = 0.7,
    version: str = "1.0",
    **kwargs: Any,
) -> G2PBase:
    """Get a G2P instance for the specified language.

    This factory function returns an appropriate G2P instance based on the
    language code. Results are cached for efficiency.

    Args:
        language: Language code (e.g., 'en-us', 'en-gb', 'zh', 'ja', 'fr', etc.).
        use_espeak_fallback: Whether to use espeak for out-of-vocabulary words
            (only applies when backend="espeak").
        use_spacy: Whether to use spaCy for tokenization and POS tagging
            (only applies to English).
        backend: Phonemization backend to use: "espeak" (default) or "goruut".
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
        multilingual_mode: If True, enable automatic language detection for
            mixed-language texts. Requires lingua-language-detector and
            allowed_languages to be specified. Example: German text with
            English words will be automatically detected and routed to the
            appropriate G2P engines.
        allowed_languages: List of languages to detect in multilingual mode.
            Required when multilingual_mode=True. Must be explicitly specified
            by the user. Example: ["de", "en-us", "fr"]. Each word will be
            analyzed and routed to the appropriate language's G2P engine.
        language_confidence_threshold: Minimum confidence (0.0-1.0) for
            language detection in multilingual mode. Words with lower confidence
            fall back to the primary language. Default: 0.7 (recommended).
        version: Model version to use. Default: "1.0" (base model).
            - "1.0": Base model
            - "1.1": Chinese/English model
            Different languages may have different behavior:
            - Chinese: "1.0" = IPA output, "1.1" = Zhuyin output
            - Other languages: Generally use "1.0" for multilingual support
        **kwargs: Additional arguments passed to the G2P constructor.

    Returns:
        A G2PBase instance for the specified language.

    Raises:
        ValueError: If the language is not supported and no fallback is available,
            or if multilingual_mode=True but allowed_languages is not specified,
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
        >>> # Mixed-language: German with English words
        >>> g2p_mixed = get_g2p(
        ...     language="de",
        ...     multilingual_mode=True,
        ...     allowed_languages=["de", "en-us"]
        ... )
        >>> result = g2p_mixed("Das Meeting ist great!")
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
    # Convert allowed_languages list to sorted tuple for hashable cache key
    allowed_langs_key = tuple(sorted(allowed_languages)) if allowed_languages else None
    cache_key = (
        f"{lang}:{use_espeak_fallback}:{use_spacy}:{backend}:{load_silver}:{load_gold}"
        f":{multilingual_mode}:{allowed_langs_key}:{language_confidence_threshold}:{version}"
    )
    if cache_key in _g2p_cache:
        return _g2p_cache[cache_key]

    # If multilingual mode is enabled, create MixedLanguageG2P
    if multilingual_mode:
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language=language,
            allowed_languages=allowed_languages,
            confidence_threshold=language_confidence_threshold,
            enable_detection=True,
            use_espeak_fallback=use_espeak_fallback,
            use_spacy=use_spacy,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
        _g2p_cache[cache_key] = g2p
        return g2p

    # Create G2P instance based on language and backend
    g2p: G2PBase

    if backend == "goruut":
        # Use goruut backend for all languages
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P(language=language, version=version, **kwargs)
    elif lang.startswith("en"):
        from kokorog2p.en import EnglishG2P

        g2p = EnglishG2P(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_spacy=use_spacy,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
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
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    else:
        # Fallback to espeak-only G2P for other languages
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language=language, version=version, **kwargs)

    _g2p_cache[cache_key] = g2p
    return g2p


def phonemize(
    text: str,
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_spacy: bool = True,
    backend: BackendType = "espeak",
) -> str:
    """Convert text to phonemes.

    This is a convenience function that creates a G2P instance and converts
    the text to a phoneme string.

    Args:
        text: Input text to convert.
        language: Language code (e.g., 'en-us', 'en-gb').
        use_espeak_fallback: Whether to use espeak for out-of-vocabulary words
            (only applies when backend="espeak").
        use_spacy: Whether to use spaCy for tokenization and POS tagging
            (only applies to English with espeak backend).
        backend: Phonemization backend to use: "espeak" (default) or "goruut".
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
        use_spacy=use_spacy,
        backend=backend,
    )
    return g2p.phonemize(text)


def tokenize(
    text: str,
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_spacy: bool = True,
    backend: BackendType = "espeak",
) -> list[GToken]:
    """Convert text to a list of tokens with phonemes.

    Args:
        text: Input text to convert.
        language: Language code (e.g., 'en-us', 'en-gb').
        use_espeak_fallback: Whether to use espeak for out-of-vocabulary words
            (only applies when backend="espeak").
        use_spacy: Whether to use spaCy for tokenization and POS tagging
            (only applies to English with espeak backend).
        backend: Phonemization backend to use: "espeak" (default) or "goruut".
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
    "MixedLanguageG2P",  # Mixed-language support
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
    # Markdown annotation support
    "phonemize_with_markdown",
    "preprocess_markdown",
    "apply_markdown_features",
    "remove_markdown",
    "LINK_REGEX",
]
