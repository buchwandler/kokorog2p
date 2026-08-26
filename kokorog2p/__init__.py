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

import warnings
from collections import OrderedDict, namedtuple
from collections.abc import Callable
from collections.abc import Sequence
from threading import RLock
from typing import Any, Literal, Optional, Union

from kokorog2p.base import G2PBase
from kokorog2p.markers import apply_marker_overrides, parse_delimited
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
from kokorog2p.integrations import (
    SegmentLike,
    coerce_override_spans,
    overrides_for_segment,
    overrides_from_ssmd,
    phonemize_segments,
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
from kokorog2p.tokenization import tokenize_with_offsets
from kokorog2p.types import OverrideSpan, OverrideSpanLike, PhonemizeResult, TokenSpan
from kokorog2p.spacy_models import (
    SpacyModelResolution,
    SpacyModelResolutionError,
    SpacyModelSize,
    normalize_spacy_language,
    resolve_spacy_model,
)

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

# Lazy imports for optional dependencies.  A small LRU preserves same-key
# reuse (including lazy spaCy model reuse) while bounding retained instances.
_G2P_CACHE_MAXSIZE = 8
_g2p_cache: OrderedDict[tuple[object, ...], G2PBase] = OrderedDict()
_g2p_cache_lock = RLock()
_G2PCacheInfo = namedtuple("_G2PCacheInfo", "size maxsize policy")

_LANGUAGE_ALIASES = {
    "en": "en-us",
    "eng": "en-us",
    "english": "en-us",
    "gb": "en-gb",
    "british": "en-gb",
    "de": "de-de",
    "de-at": "de-de",
    "de-ch": "de-de",
    "deu": "de-de",
    "german": "de-de",
    "fr": "fr-fr",
    "fra": "fr-fr",
    "french": "fr-fr",
    "es": "es-es",
    "spa": "es-es",
    "spanish": "es-es",
    "it": "it-it",
    "ita": "it-it",
    "italian": "it-it",
    "pt": "pt-br",
    "por": "pt-br",
    "portuguese": "pt-br",
    "cs": "cs-cz",
    "ces": "cs-cz",
    "czech": "cs-cz",
    "vi": "vi-vn",
    "vi-vn": "vi-vn",
    "vie": "vi-vn",
    "vietnamese": "vi-vn",
    "ko": "ko-kr",
    "kor": "ko-kr",
    "korean": "ko-kr",
    "he": "he",
    "heb": "he",
    "hebrew": "he",
    "zh": "zh",
    "cmn": "zh",
    "chinese": "zh",
    "ja": "ja-jp",
    "jpn": "ja-jp",
    "japanese": "ja-jp",
}

_FACTORY_KWARGS_BY_LANGUAGE = {
    "en": frozenset({"expand_abbreviations", "enable_context_detection", "unk"}),
    "fr": frozenset(
        {"expand_nums", "expand_abbreviations", "enable_context_detection", "unk"}
    ),
    "de": frozenset(
        {
            "use_lexicon",
            "strip_stress",
            "expand_abbreviations",
            "enable_context_detection",
        }
    ),
    "cs": frozenset({"unk", "expand_abbreviations", "enable_context_detection"}),
    "es": frozenset({"expand_abbreviations", "enable_context_detection"}),
    "it": frozenset(
        {
            "mark_stress",
            "mark_gemination",
            "expand_abbreviations",
            "enable_context_detection",
        }
    ),
    "pt": frozenset(
        {
            "mark_stress",
            "affricate_ti_di",
            "expand_abbreviations",
            "enable_context_detection",
            "dialect",
        }
    ),
    "he": frozenset({"preserve_punctuation", "preserve_stress", "some_extra_param"}),
    "ko": frozenset(
        {
            "voice",
            "morphology",
            "morphology_backend",
            "descriptive",
            "use_dict",
            "group_vowels",
            "to_syl",
            "output",
            "model_profile",
        }
    ),
    "vi": frozenset({"foreign_fallback"}),
}

_SPACY_DEFAULTS_BY_FAMILY = {
    "en": True,
    "fr": True,
    "de": False,
    "es": False,
    "it": False,
    "pt": False,
}
_SPACY_MODEL_FAMILIES = frozenset(_SPACY_DEFAULTS_BY_FAMILY)

# Backend type hint
BackendType = Literal["kokorog2p", "espeak", "goruut"]


def _canonical_language(language: str) -> str:
    """Return the cache identity for a language alias."""
    normalized = language.lower().replace("_", "-")
    return _LANGUAGE_ALIASES.get(normalized, normalized)


def _language_family(language: str) -> str:
    """Return the factory option family for a canonical language."""
    if language.startswith("en"):
        return "en"
    return language.split("-", 1)[0]


def _resolve_factory_spacy(
    language: str,
    backend: BackendType,
    requested: bool | None,
    spacy_model: str | None,
    spacy_model_size: SpacyModelSize | None,
) -> tuple[bool, str | None]:
    """Resolve optional or required spaCy use for a native language factory.

    Automatic resolution is intentionally optional when ``requested`` is
    ``None``. Explicit enablement, an exact model, or an exact model size is
    strict and preserves the resolver's actionable error when unavailable.
    """

    default_enabled = _SPACY_DEFAULTS_BY_FAMILY.get(_language_family(language), False)
    wants_spacy = default_enabled if requested is None else requested

    if backend != "kokorog2p":
        return False, None

    if _language_family(language) not in _SPACY_MODEL_FAMILIES:
        return bool(requested), None

    if not wants_spacy:
        if not wants_spacy and (
            spacy_model not in (None, "", "auto") or spacy_model_size is not None
        ):
            warnings.warn(
                "spaCy model arguments are ignored when use_spacy=False.",
                RuntimeWarning,
                stacklevel=3,
            )
        return False, None

    strict_request = (
        requested is True
        or spacy_model not in (None, "", "auto")
        or spacy_model_size is not None
    )
    try:
        resolution = resolve_spacy_model(
            language,
            spacy_model=spacy_model or None,
            spacy_model_size=spacy_model_size,
        )
    except SpacyModelResolutionError:
        if strict_request:
            raise
        return False, None
    return True, resolution.package


def _forward_factory_spacy_model(
    language: str, requested: str | None, resolved: str | None
) -> str | None:
    """Return the model name passed to a native G2P constructor.

    Korean keeps this reserved option for API compatibility without resolving
    or loading a spaCy model.
    """

    if resolved is not None:
        return resolved
    if _language_family(language) == "ko":
        return requested
    return None


def _validate_factory_kwargs(
    language: str, backend: BackendType, kwargs: dict[str, Any]
) -> None:
    """Reject options that constructors would silently ignore."""
    if not kwargs:
        return
    if backend in ("espeak", "goruut"):
        allowed: frozenset[str] = frozenset()
    else:
        allowed = _FACTORY_KWARGS_BY_LANGUAGE.get(
            _language_family(language), frozenset()
        )
    unknown = sorted(set(kwargs) - allowed)
    if unknown:
        names = ", ".join(unknown)
        raise TypeError(f"Unsupported get_g2p options: {names}")


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


def get_g2p(  # noqa: C901
    language: str = "en-us",
    use_espeak_fallback: bool = True,
    use_goruut_fallback: bool = False,
    use_cli: bool = False,
    use_spacy: bool | None = None,
    backend: BackendType = "kokorog2p",
    load_silver: bool = True,
    load_gold: bool = True,
    version: str = "1.0",
    phoneme_quotes: str = "curly",
    strict: bool = True,
    spacy_model: str | None = None,
    spacy_model_size: SpacyModelSize | None = None,
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
        use_spacy: Whether to use spaCy for tokenization and POS tagging. If
            ``None``, the highest-quality installed and loadable local model is
            attempted for languages with spaCy defaults and the native path is
            used when no model is available. ``True`` requires a loadable model;
            ``False`` forces the native path. No model is downloaded automatically.
        spacy_model: Concrete spaCy model package name, or ``"auto"`` for the
            highest installed loadable tier. Concrete names are strict.
        spacy_model_size: Exact model tier (``"trf"``, ``"lg"``, ``"md"``, or
            ``"sm"``) to select when ``spacy_model`` is unset.
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
    # Normalize language code before constructing the cache key.  The
    # canonical value is also passed to implementations so aliases that are
    # behaviorally equivalent do not create duplicate instances or voices.
    requested_language = language.lower().replace("_", "-")
    lang = _canonical_language(language)
    # Validate version parameter
    if version not in ("1.0", "1.1"):
        raise ValueError(
            f"Invalid version '{version}'. "
            "Must be '1.0' (multilngual) or '1.1' (chinese)."
        )

    backend = backend.lower()  # type: ignore[assignment]
    if backend not in ("kokorog2p", "espeak", "goruut"):
        raise ValueError(f"Unsupported backend: {backend!r}")
    _validate_factory_kwargs(lang, backend, kwargs)
    implementation_language = (
        lang if backend in ("espeak", "goruut") else requested_language
    )

    # Resolve before touching the cache. The native CJK implementations accept
    # spaCy arguments for API consistency but do not use spaCy at all.
    effective_use_spacy, resolved_spacy_model = _resolve_factory_spacy(
        lang, backend, use_spacy, spacy_model, spacy_model_size
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
    # An explicit model is irrelevant when spaCy is disabled for spaCy-backed
    # languages. Korean is a reserved API case: it does not load spaCy, but it
    # retains and forwards the configured model name for compatibility.
    forwarded_spacy_model = _forward_factory_spacy_model(
        lang, spacy_model, resolved_spacy_model
    )
    cache_key = (
        lang,
        use_espeak_fallback,
        use_goruut_fallback,
        use_cli,
        effective_use_spacy,
        forwarded_spacy_model,
        backend,
        load_silver,
        load_gold,
        version,
        phoneme_quotes,
        strict,
        kwargs_key,
    )

    with _g2p_cache_lock:
        cached = _g2p_cache.get(cache_key)
        if cached is not None:
            _g2p_cache.move_to_end(cache_key)
            return cached

    # Create G2P instance based on language and backend
    g2p: G2PBase
    extra_kwargs: dict[str, Any] = (
        {"spacy_model": forwarded_spacy_model}
        if forwarded_spacy_model is not None
        else {}
    )

    if backend == "goruut":
        # Use goruut backend for all languages
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P(
            language=implementation_language, strict=strict, version=version, **kwargs
        )
    elif backend == "espeak":
        # Use espeak backend for all languages
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(
            language=implementation_language,
            strict=strict,
            version=version,
            use_cli=use_cli,
            **kwargs,
        )

    elif lang.startswith("en"):
        from kokorog2p.en import EnglishG2P

        g2p = EnglishG2P(
            language=implementation_language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
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
            language=implementation_language,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("ja", "ja-jp", "jpn", "japanese"):
        from kokorog2p.ja import JapaneseG2P

        g2p = JapaneseG2P(
            language=implementation_language,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("fr", "fr-fr", "fra", "french"):
        from kokorog2p.fr import FrenchG2P

        g2p = FrenchG2P(
            language=implementation_language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("es", "es-es", "spa", "spanish"):
        from kokorog2p.es import SpanishG2P

        g2p = SpanishG2P(
            language=implementation_language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            version=version,
            **kwargs,
        )
    elif lang in ("it", "it-it", "ita", "italian"):
        from kokorog2p.it import ItalianG2P

        g2p = ItalianG2P(
            language=implementation_language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            version=version,
            **kwargs,
        )
    elif lang in ("pt", "pt-br", "pt-pt", "por", "portuguese"):
        from kokorog2p.pt import PortugueseG2P

        g2p = PortugueseG2P(
            language=implementation_language,
            use_espeak_fallback=use_espeak_fallback,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            version=version,
            **kwargs,
        )
    elif lang in ("cs", "cs-cz", "ces", "czech"):
        from kokorog2p.cs import CzechG2P

        g2p = CzechG2P(
            language=implementation_language,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("de", "de-de", "de-at", "de-ch", "deu", "german"):
        from kokorog2p.de import GermanG2P

        g2p = GermanG2P(
            language=implementation_language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang == "vi-vn":
        from kokorog2p.vi import VietnameseG2P

        g2p = VietnameseG2P(
            language="vi-vn",
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            strict=strict,
            version=version,
            **kwargs,
        )
    elif lang in ("ko", "ko-kr", "kor", "korean"):
        from kokorog2p.ko import KoreanG2P

        g2p = KoreanG2P(
            language=implementation_language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_spacy=effective_use_spacy,
            **extra_kwargs,
            load_silver=load_silver,
            load_gold=load_gold,
            version=version,
            **kwargs,
        )
    elif lang in ("he", "he-il", "heb", "hebrew"):
        from kokorog2p.he import HebrewG2P

        g2p = HebrewG2P(
            language=implementation_language,
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

    with _g2p_cache_lock:
        # A second lookup protects identity if another thread constructed the
        # same key while this instance was being initialized.
        cached = _g2p_cache.get(cache_key)
        if cached is not None:
            _g2p_cache.move_to_end(cache_key)
            return cached
        _g2p_cache[cache_key] = g2p
        _g2p_cache.move_to_end(cache_key)
        while len(_g2p_cache) > _G2P_CACHE_MAXSIZE:
            _g2p_cache.popitem(last=False)
        return g2p


def phonemize(
    text: str,
    language: str = "en-us",
    *,
    overrides: Sequence[OverrideSpanLike] | None = None,
    return_ids: bool = True,
    return_phonemes: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    overlap: Literal["snap", "strict"] = "snap",
    use_normalizer_rules: bool = True,
    use_espeak_fallback: bool = True,
    use_goruut_fallback: bool = False,
    use_cli: bool = False,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    spacy_model_size: SpacyModelSize | None = None,
    load_silver: bool = True,
    load_gold: bool = True,
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
            tokenization/POS tagging (English/French and optionally German).
            For Chinese/Japanese/Korean, this flag is accepted for API
            consistency but currently does not alter backend behavior.
            Ignored if ``g2p`` is
            provided.
        spacy_model:
            Concrete spaCy model package or ``"auto"`` when constructing a G2P
            instance. If omitted, the highest installed loadable model is used
            when spaCy is enabled. For Chinese/Japanese/Korean, accepted for
            API consistency but not currently used by native backends.
        spacy_model_size:
            Exact spaCy model tier to use when ``spacy_model`` is omitted.
        load_silver:
            Whether to load the optional silver dictionary when constructing a
            G2P instance.
        load_gold:
            Whether to load the optional gold dictionary when constructing a
            G2P instance.
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
            spacy_model=spacy_model,
            spacy_model_size=spacy_model_size,
            load_silver=load_silver,
            load_gold=load_gold,
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
        g2p_options={
            "use_espeak_fallback": use_espeak_fallback,
            "use_goruut_fallback": use_goruut_fallback,
            "use_cli": use_cli,
            "use_spacy": use_spacy,
            "spacy_model": spacy_model,
            "spacy_model_size": spacy_model_size,
            "backend": backend,
        },
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


def cache_info():
    """Return diagnostics for the weak G2P instance cache.

    The bounded LRU keeps the most recently used configurations and evicts
    older instances once the configured maximum is reached.
    """
    with _g2p_cache_lock:
        return _G2PCacheInfo(
            size=len(_g2p_cache), maxsize=_G2P_CACHE_MAXSIZE, policy="bounded-lru"
        )


def clear_cache(*, deep: bool = False) -> None:
    """Clear the G2P instance cache.

    Args:
        deep: Also clear language dictionary resource caches.  This can be
            useful when a long-running process must release parsed lexicons.
    """
    with _g2p_cache_lock:
        _g2p_cache.clear()

    if deep:
        from kokorog2p.de.lexicon import clear_lexicon_cache as clear_de
        from kokorog2p.en.lexicon import clear_lexicon_cache as clear_en
        from kokorog2p.fr.lexicon import clear_lexicon_cache as clear_fr

        clear_en()
        clear_fr()
        clear_de()


def reset_abbreviations() -> None:
    """Reset abbreviation expanders to their default state."""
    from abbr2words import reset_expanders

    reset_expanders()

    clear_cache(deep=True)

    from kokorog2p import pipeline_api

    pipeline_api._get_abbreviation_expander.cache_clear()
    pipeline_api._get_language_normalizer.cache_clear()


# Public API
__all__ = [
    "CONSONANTS",
    "GB_VOCAB",
    "KOKORO_PUNCTUATION",
    "N_TOKENS",
    "PAD_IDX",
    "US_VOCAB",
    "VOWELS",
    "G2PBase",
    "GToken",
    "MismatchInfo",
    "MismatchMode",
    "MismatchStats",
    "OverrideSpan",
    "OverrideSpanLike",
    "PhonemizeResult",
    "Punctuation",
    "SegmentLike",
    "SpacyModelResolution",
    "SpacyModelResolutionError",
    "SpacyModelSize",
    "TokenSpan",
    "__version__",
    "__version_tuple__",
    "apply_marker_overrides",
    "cache_info",
    "check_word_alignment",
    "clear_cache",
    "coerce_override_spans",
    "count_words",
    "decode",
    "detect_mismatches",
    "encode",
    "filter_for_kokoro",
    "filter_punctuation",
    "from_espeak",
    "from_goruut",
    "get_g2p",
    "get_kokoro_config",
    "get_kokoro_vocab",
    "get_vocab",
    "ids_to_phonemes",
    "is_kokoro_punctuation",
    "normalize_punctuation",
    "normalize_spacy_language",
    "overrides_for_segment",
    "overrides_from_ssmd",
    "parse_delimited",
    "phoneme_ids",
    "phonemes",
    "phonemes_to_ids",
    "phonemize",
    "phonemize_segments",
    "preprocess_multilang",
    "reset_abbreviations",
    "resolve_spacy_model",
    "to_espeak",
    "tokenize",
    "validate_for_kokoro",
    "validate_phonemes",
]
