"""Language annotation preprocessing using lingua-py.

This module detects word-level languages and adds language override
annotations to the input text for use with kokorog2p's span-based API.

Example:
    >>> from kokorog2p.multilang import preprocess_multilang
    >>> preprocess_multilang("Schöne World", default_language="en-us",
        allowed_languages=["en-us", "de"])
    # Returns list of OverrideSpan objects for language switching
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any, Final

from kokorog2p.types import OverrideSpan

try:
    from lingua import Language, LanguageDetectorBuilder

    LINGUA_AVAILABLE = True
except ImportError:  # pragma: no cover - tested via import guard
    LINGUA_AVAILABLE = False
    Language = None  # type: ignore
    LanguageDetectorBuilder = None  # type: ignore


WORD_OR_PUNCT_REGEX = re.compile(r"\w+|\s+|[^\w\s]+", re.UNICODE)

# Map kokorog2p language codes to lingua Language enum
KOKOROG2P_TO_LINGUA: Final[dict[str, Any]] = {}
LINGUA_TO_KOKOROG2P: Final[dict[Any, str]] = {}

if LINGUA_AVAILABLE:
    KOKOROG2P_TO_LINGUA.update(
        {
            "en": Language.ENGLISH,  # type: ignore
            "en-us": Language.ENGLISH,  # type: ignore
            "en-gb": Language.ENGLISH,  # type: ignore
            "de": Language.GERMAN,  # type: ignore
            "de-de": Language.GERMAN,  # type: ignore
            "de-at": Language.GERMAN,  # type: ignore
            "de-ch": Language.GERMAN,  # type: ignore
            "fr": Language.FRENCH,  # type: ignore
            "fr-fr": Language.FRENCH,  # type: ignore
            "es": Language.SPANISH,  # type: ignore
            "es-es": Language.SPANISH,  # type: ignore
            "it": Language.ITALIAN,  # type: ignore
            "pt": Language.PORTUGUESE,  # type: ignore
            "pt-br": Language.PORTUGUESE,  # type: ignore
            "ja": Language.JAPANESE,  # type: ignore
            "ja-jp": Language.JAPANESE,  # type: ignore
            "zh": Language.CHINESE,  # type: ignore
            "zh-cn": Language.CHINESE,  # type: ignore
            "zh-tw": Language.CHINESE,  # type: ignore
            "ko": Language.KOREAN,  # type: ignore
            "ko-kr": Language.KOREAN,  # type: ignore
            "he": Language.HEBREW,  # type: ignore
            "he-il": Language.HEBREW,  # type: ignore
            "cs": Language.CZECH,  # type: ignore
            "cs-cz": Language.CZECH,  # type: ignore
            "nl": Language.DUTCH,  # type: ignore
            "pl": Language.POLISH,  # type: ignore
            "ru": Language.RUSSIAN,  # type: ignore
            "ar": Language.ARABIC,  # type: ignore
            "hi": Language.HINDI,  # type: ignore
            "tr": Language.TURKISH,  # type: ignore
        }
    )

    LINGUA_TO_KOKOROG2P.update(
        {
            Language.ENGLISH: "en-us",  # type: ignore
            Language.GERMAN: "de",  # type: ignore
            Language.FRENCH: "fr",  # type: ignore
            Language.SPANISH: "es",  # type: ignore
            Language.ITALIAN: "it",  # type: ignore
            Language.PORTUGUESE: "pt",  # type: ignore
            Language.JAPANESE: "ja",  # type: ignore
            Language.CHINESE: "zh",  # type: ignore
            Language.KOREAN: "ko",  # type: ignore
            Language.HEBREW: "he",  # type: ignore
            Language.CZECH: "cs",  # type: ignore
            Language.DUTCH: "nl",  # type: ignore
            Language.POLISH: "pl",  # type: ignore
            Language.RUSSIAN: "ru",  # type: ignore
            Language.ARABIC: "ar",  # type: ignore
            Language.HINDI: "hi",  # type: ignore
            Language.TURKISH: "tr",  # type: ignore
        }
    )


def _normalize_language(code: str) -> str:
    return code.lower().replace("_", "-")


def _map_to_lingua_languages(lang_codes: list[str]) -> list[Any]:
    result: list[Any] = []
    seen: set[Any] = set()
    for code in lang_codes:
        normalized = _normalize_language(code)
        if normalized in KOKOROG2P_TO_LINGUA:
            lingua_lang = KOKOROG2P_TO_LINGUA[normalized]
            if lingua_lang not in seen:
                result.append(lingua_lang)
                seen.add(lingua_lang)
    return result


def _map_from_lingua_language(lingua_lang: Any, allowed: list[str]) -> str:
    base_code = LINGUA_TO_KOKOROG2P.get(lingua_lang)
    if base_code is None:
        return allowed[0]
    for allowed_code in allowed:
        if allowed_code == base_code or allowed_code.startswith(base_code + "-"):
            return allowed_code
    return base_code


def _pick_allowed_language(base_code: str, allowed: list[str]) -> str | None:
    for allowed_code in allowed:
        if allowed_code == base_code or allowed_code.startswith(base_code + "-"):
            return allowed_code
    return None


def _detect_script_language(token: str, allowed: list[str]) -> str | None:
    if re.search(r"[\uac00-\ud7a3]", token):
        return _pick_allowed_language("ko", allowed)
    if re.search(r"[\u3040-\u30ff\u31f0-\u31ff]", token):
        return _pick_allowed_language("ja", allowed)
    if re.search(r"[\u4e00-\u9fff]", token):
        return _pick_allowed_language("zh", allowed) or _pick_allowed_language(
            "ja", allowed
        )
    if re.search(r"[\u0590-\u05ff]", token):
        return _pick_allowed_language("he", allowed)
    return None


def _validate_languages(
    default_language: str,
    allowed_languages: list[str] | None,
) -> tuple[list[str], str, list[Any]]:
    if allowed_languages is None or len(allowed_languages) == 0:
        raise ValueError("allowed_languages must be specified and non-empty")

    normalized_allowed = [_normalize_language(lang) for lang in allowed_languages]
    normalized_default = _normalize_language(default_language)
    if normalized_default not in normalized_allowed:
        raise ValueError("default_language must be in allowed_languages")

    lingua_languages = _map_to_lingua_languages(normalized_allowed)
    if not lingua_languages:
        raise ValueError("allowed_languages do not map to lingua languages")

    return normalized_allowed, normalized_default, lingua_languages


def _build_language_detector(lingua_languages: list[Any]) -> Any:
    return (
        LanguageDetectorBuilder.from_languages(*lingua_languages)  # type: ignore
        .with_preloaded_language_models()
        .build()
    )


def _make_language_detector(
    detector: Any,
    normalized_allowed: list[str],
    normalized_default: str,
    confidence_threshold: float,
    min_token_length: int,
) -> Callable[[str], str]:
    cache: dict[str, str] = {}

    def detect_language(word: str) -> str:
        script_lang = _detect_script_language(word, normalized_allowed)
        if script_lang:
            return script_lang
        if len(word) < min_token_length or not any(c.isalnum() for c in word):
            return normalized_default
        if word in cache:
            return cache[word]

        confidence_values = detector.compute_language_confidence_values(word)
        if not confidence_values:
            cache[word] = normalized_default
            return normalized_default

        best_match = confidence_values[0]
        if best_match.value < confidence_threshold:
            cache[word] = normalized_default
            return normalized_default

        detected = _map_from_lingua_language(best_match.language, normalized_allowed)
        if detected not in normalized_allowed:
            detected = normalized_default

        cache[word] = detected
        return detected

    return detect_language


def _overlaps_range(
    start: int,
    end: int,
    covered_ranges: list[tuple[int, int]],
) -> bool:
    return any(
        start < span_end and end > span_start for span_start, span_end in covered_ranges
    )


def _collect_phrase_overrides(
    text: str,
    phrase_overrides: dict[str, str] | None,
    normalized_allowed: list[str],
) -> tuple[list[OverrideSpan], list[tuple[int, int]]]:
    overrides: list[OverrideSpan] = []
    covered_ranges: list[tuple[int, int]] = []
    if not phrase_overrides:
        return overrides, covered_ranges

    for phrase, lang_code in phrase_overrides.items():
        if not phrase:
            continue
        normalized_lang = _normalize_language(lang_code)
        if normalized_lang not in normalized_allowed:
            continue
        for match in re.finditer(re.escape(phrase), text):
            start = match.start()
            end = match.end()
            if _overlaps_range(start, end, covered_ranges):
                continue
            overrides.append(
                OverrideSpan(
                    char_start=start,
                    char_end=end,
                    attrs={"lang": normalized_lang},
                )
            )
            covered_ranges.append((start, end))

    return overrides, covered_ranges


def _collect_token_overrides(
    text: str,
    detect_language: Callable[[str], str],
    normalized_default: str,
    covered_ranges: list[tuple[int, int]],
) -> list[OverrideSpan]:
    overrides: list[OverrideSpan] = []
    offset = 0

    for token in WORD_OR_PUNCT_REGEX.findall(text):
        token_start = offset
        token_end = offset + len(token)
        offset = token_end

        if token.isspace():
            continue

        if _overlaps_range(token_start, token_end, covered_ranges):
            continue

        if not any(ch.isalnum() for ch in token):
            continue

        trimmed = re.sub(r"^\W+|\W+$", "", token, flags=re.UNICODE)
        detect_text = trimmed if trimmed else token
        if not detect_text:
            continue

        detected = detect_language(detect_text)
        if detected != normalized_default:
            overrides.append(
                OverrideSpan(
                    char_start=token_start,
                    char_end=token_end,
                    attrs={"lang": detected},
                )
            )

    return overrides


def _dedupe_overrides(overrides: list[OverrideSpan]) -> list[OverrideSpan]:
    if not overrides:
        return overrides

    seen: set[tuple[int, int, str]] = set()
    deduped: list[OverrideSpan] = []
    for override in sorted(overrides, key=lambda o: (o.char_start, o.char_end)):
        lang_value = override.attrs.get("lang", "")
        key = (override.char_start, override.char_end, lang_value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(override)

    return deduped


def preprocess_multilang(
    text: str,
    default_language: str = "en-us",
    allowed_languages: list[str] | None = None,
    confidence_threshold: float = 0.7,
    phrase_overrides: dict[str, str] | None = None,
    min_token_length: int = 3,
) -> list[OverrideSpan]:
    """Detect word-level languages and return OverrideSpan objects.

    Returns OverrideSpan objects for language switching.

    Args:
        text: Input text to annotate.
        default_language: Base language for unmarked words.
        allowed_languages: Language codes to detect (must include default_language).
        confidence_threshold: Minimum confidence (0.0-1.0) to accept detection.
        phrase_overrides: Optional dict mapping exact phrases to language codes.
        min_token_length: Minimum token length for detection (default: 3).

    Returns:
        List of OverrideSpan objects with language overrides for detected words.

    Raises:
        ImportError: If lingua-language-detector is not installed.
        ValueError: If allowed_languages is missing or default_language not allowed.
    """
    if not LINGUA_AVAILABLE:
        raise ImportError(
            "lingua-language-detector is required for preprocess_multilang. "
            "Install with: pip install lingua-language-detector"
        )

    normalized_allowed, normalized_default, lingua_languages = _validate_languages(
        default_language,
        allowed_languages,
    )
    detector = _build_language_detector(lingua_languages)
    detect_language = _make_language_detector(
        detector,
        normalized_allowed,
        normalized_default,
        confidence_threshold,
        min_token_length,
    )

    overrides, covered_ranges = _collect_phrase_overrides(
        text,
        phrase_overrides,
        normalized_allowed,
    )
    overrides.extend(
        _collect_token_overrides(
            text,
            detect_language,
            normalized_default,
            covered_ranges,
        )
    )

    return _dedupe_overrides(overrides)


__all__ = ["preprocess_multilang"]
