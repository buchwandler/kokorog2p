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
from kokorog2p.multilang import preprocess_multilang
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

# New span-based API
from kokorog2p.pipeline_api import phonemize_to_result

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
from kokorog2p.tokenization import tokenize_with_offsets
from kokorog2p.types import OverrideSpan, PhonemizeResult, TokenSpan

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
_g2p_cache: dict[tuple[object, ...], G2PBase] = {}

# Backend type hint
BackendType = Literal["kokorog2p", "espeak", "goruut"]


def _stable_repr(value: Any) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return repr(value)
    if isinstance(value, list | tuple):
        return tuple(_stable_repr(item) for item in value)
    if isinstance(value, dict):
        dict_items = [
            (_stable_repr(key), _stable_repr(val)) for key, val in value.items()
        ]
        return tuple(sorted(dict_items, key=repr))
    if isinstance(value, set | frozenset):
        set_items = [_stable_repr(item) for item in value]
        return tuple(sorted(set_items, key=repr))
    return repr(value)


def get_g2p(
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_goruut_fallback: bool = False,
    use_cli: bool = False,
    use_spacy: bool = True,
    backend: BackendType = "kokorog2p",
    load_silver: bool = True,
    load_gold: bool = True,
    version: str = "1.0",
    phoneme_quotes: str = "curly",
    strict: bool = True,
    **kwargs: Any,
) -> G2PBase:
    """Get a G2P instance for the specified language.

    This factory function returns an appropriate G2P instance based on the
    language code. Results are cached for efficiency. For mixed-language text,
    use preprocess_multilang to generate OverrideSpan objects for phonemize_to_result.

    Args:
        language: Language code (e.g., 'en-us', 'en-gb', 'zh', 'ja', 'fr', etc.).
        use_espeak_fallback: Whether to use espeak for out-of-vocabulary words
            when using the dictionary-based "kokorog2p" backend. Ignored when
            backend is set to "espeak" (espeak is the primary backend).
        use_goruut_fallback: Whether to use goruut for out-of-vocabulary words
            when using the dictionary-based "kokorog2p" backend. Ignored when
            backend is set to "goruut" (goruut is the primary backend).
        use_spacy: Whether to use spaCy for tokenization and POS tagging
            (only applies to English). Used by the "kokorog2p" backend.
        use_cli: If True, force use of CLI espeak phonemizer instead of
            library bindings. Only applies when backend="espeak".
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
    kwargs_key = None
    if kwargs:
        kwargs_key = tuple(
            sorted(
                ((key, _stable_repr(value)) for key, value in kwargs.items()),
                key=lambda item: item[0],
            )
        )
    cache_key = (
        lang,
        use_espeak_fallback,
        use_goruut_fallback,
        use_cli,
        use_spacy,
        backend,
        load_silver,
        load_gold,
        version,
        phoneme_quotes,
        strict,
        kwargs_key,
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

        g2p = EspeakOnlyG2P(
            language=language, strict=strict, version=version, use_cli=use_cli, **kwargs
        )

    elif lang.startswith("en"):
        from kokorog2p.en import EnglishG2P

        g2p = EnglishG2P(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
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

    _g2p_cache[cache_key] = g2p
    return g2p


def phonemize(
    text: str,
    language: str = "en-us",
    *,
    overrides: list[OverrideSpan] | None = None,
    return_ids: bool = True,
    return_phonemes: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    overlap: Literal["snap", "strict"] = "snap",
    use_normalizer_rules: bool = True,
    use_espeak_fallback: bool = True,
    use_goruut_fallback: bool = False,
    use_cli: bool = False,
    use_spacy: bool = True,
    backend: "BackendType" = "kokorog2p",
    g2p: "G2PBase | None" = None,
) -> PhonemizeResult:
    """Phonemize text using the unified kokorog2p pipeline.

    This is the primary public entry point for turning text into phonemes (and
    optionally tokens or token IDs) in a consistent way.

    Internally, this function delegates to the same implementation used by
    span-based override phonemization (the former ``phonemize_to_result`` path),
    ensuring that:

    - The phoneme string returned here is identical to the one in the returned
      :class:`~kokorog2p.types.PhonemizeResult`.
    - Tokenization and character offsets are deterministic and match the
      phoneme output.
    - Kokoro-model vocabulary validation/filtering is applied when producing
      token IDs (and when necessary to make the phoneme string ID-safe).

    Args:
        text:
            Input text to phonemize. This should be plain text (no markup).
            Punctuation may be normalized (e.g. ``...`` → ``…``, ``-`` → ``—``)
            to match Kokoro-compatible forms.
        language:
            Language code (e.g. ``"en-us"``, ``"en-gb"``, ``"de"``, ``"fr"``).
            Used both for tokenization/alignment and for constructing a default
            G2P instance when ``g2p`` is not provided.
        overrides:
            Optional span-based overrides applied by character offsets.
            Overrides can inject phonemes (``{"ph": "…"}``) and/or change the
            language of a span (``{"lang": "de"}``) for that region.
        return_ids:
            Whether to include token IDs in the returned result.
        return_phonemes:
            Whether to include the phoneme string in the returned result.
        alignment:
            Alignment mode for applying overrides and token offsets:

            - ``"span"`` (default): deterministic offset-based alignment using
              :func:`~kokorog2p.pipeline.tokenize`.
            - ``"legacy"``: backward-compatible alignment based on the backend's
              own tokenization. This may differ slightly across backends and
              languages.
        overlap:
            How to handle overrides that partially overlap a token boundary:

            - ``"snap"`` (default): apply to intersecting tokens and emit a
              warning when boundaries only partially overlap.
            - ``"strict"``: skip partial overlaps and emit a warning.
        use_normalizer_rules:
            Whether to apply language normalizer rules when building the internal
            alignment text used for span mapping.
        use_espeak_fallback:
            When constructing a G2P instance for the dictionary-based
            ``"kokorog2p"`` backend, fall back to eSpeak for out-of-vocabulary
            words. Ignored if ``g2p`` is provided.
        use_goruut_fallback:
            When constructing a G2P instance for the dictionary-based
            ``"kokorog2p"`` backend, fall back to goru·ut for out-of-vocabulary
            words. Ignored if ``g2p`` is provided.
        use_spacy:
            When constructing a G2P instance, whether to use spaCy for
            tokenization/POS tagging (English only). Ignored if ``g2p`` is
            provided.
        backend:
            When constructing a G2P instance, select the backend:
            ``"kokorog2p"``, ``"espeak"``, or ``"goruut"``. Ignored if ``g2p`` is
            provided.
        g2p:
            Optional pre-created G2P instance to reuse across calls (useful for
            caching/performance). If provided, this function will use it directly
            and will NOT call :func:`~kokorog2p.get_g2p` (so ``backend`` and the
            fallback/spaCy construction flags are ignored for this call).

    Returns:
        A :class:`~kokorog2p.types.PhonemizeResult` containing tokens, phonemes,
        token_ids, and warnings (depending on ``return_*`` flags).

    Examples:
        Basic phonemization:

        >>> phonemize("Hello world!", language="en-us").phonemes
        'h…'

        Token IDs (model-ready):

        >>> phonemize("Hello world!").token_ids
        [ ... ]

        Reusing a cached G2P instance:

        >>> g2p = get_g2p(language="en-us")
        >>> phonemize("Hello world!", g2p=g2p).phonemes
        'h…'

        Full traceable result (tokens + warnings):

        >>> span = [OverrideSpan(6, 10, {"lang": "de"})]
        >>> r = phonemize("Hello Welt!", overrides=span)
        >>> r.tokens[1].lang
        'de'
    """
    if g2p is None:
        g2p = get_g2p(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            use_spacy=use_spacy,
            backend=backend,
        )

    return phonemize_to_result(
        clean_text=text,
        lang=language,
        overrides=overrides,
        return_ids=return_ids,
        return_phonemes=return_phonemes,
        alignment=alignment,
        overlap=overlap,
        use_normalizer_rules=use_normalizer_rules,
        g2p=g2p,
    )


def phonemes(*args: Any, **kwargs: Any) -> str:
    """Get phoneme string from text using phonemize()."""
    return (
        phonemize(*args, **kwargs, return_phonemes=True, return_ids=False).phonemes
        or ""
    )


def phoneme_ids(*args: Any, **kwargs: Any) -> list[int]:
    """Get token IDs from text using phonemize()."""
    return (
        phonemize(*args, **kwargs, return_phonemes=False, return_ids=True).token_ids
        or []
    )


def tokenize(
    text: str,
    language: str = "en-us",
    *,
    keep_punct: bool = True,
) -> list[TokenSpan]:
    """Convert text to a list of tokens with phonemes.

    Args:
        text: Input text to convert.
        language: Language code (e.g., 'en-us', 'en-gb').
        keep_punct: Whether to include punctuation tokens.

    Returns:
        List of TokenSpan objects with char offsets.

    Example:
        >>> tokens = tokenize("Hello world!", language="en-us")
        >>> for t in tokens:
        ...     print(f"{t.text} [{t.char_start}:{t.char_end}]")
        Hello [0:5]
        world [6:11]
        ! [11:12]
    """

    # same as tokenize_with_offsets + punctuation normalization
    text = normalize_punctuation(text)
    return tokenize_with_offsets(text, lang=language, keep_punct=keep_punct)


def clear_cache() -> None:
    """Clear the G2P instance cache.

    This can be useful when you need to free memory or reset state.
    """
    _g2p_cache.clear()


def reset_abbreviations() -> None:
    """Reset abbreviation expanders to their default state."""
    from kokorog2p.cs.abbreviations import reset_expander as reset_cs
    from kokorog2p.de.abbreviations import reset_expander as reset_de
    from kokorog2p.en.abbreviations import reset_expander as reset_en
    from kokorog2p.es.abbreviations import reset_expander as reset_es
    from kokorog2p.fr.abbreviations import reset_expander as reset_fr
    from kokorog2p.it.abbreviations import reset_expander as reset_it
    from kokorog2p.pt.abbreviations import reset_expander as reset_pt

    reset_cs()
    reset_de()
    reset_en()
    reset_es()
    reset_fr()
    reset_it()
    reset_pt()

    _g2p_cache.clear()

    from kokorog2p import pipeline_api

    pipeline_api._get_abbreviation_expander.cache_clear()
    pipeline_api._get_language_normalizer.cache_clear()


# Marker-based helper
from kokorog2p.markers import apply_marker_overrides  # noqa: E402
from kokorog2p.markers import parse_delimited  # noqa: E402

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
    "phonemes",
    "phoneme_ids",
    "get_g2p",
    "clear_cache",
    "reset_abbreviations",
    # New span-based API (recommended for pipelines)
    "TokenSpan",
    "OverrideSpan",
    "PhonemizeResult",
    # Marker-based helper
    "parse_delimited",
    "apply_marker_overrides",
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
    # Multi-language support
    "preprocess_multilang",
]
