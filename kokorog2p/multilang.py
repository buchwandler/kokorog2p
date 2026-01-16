"""SSMD language annotation preprocessing using lingua-py.

This module detects word-level languages and adds SSMD {lang="..."}
annotations to the input text. Users are expected to call this preprocessor
before phonemization.

Example:
    >>> from kokorog2p.multilang import preprocess_multilang
    >>> preprocess_multilang("Schöne World", default_language="en-us",
        allowed_languages=["en-us", "de"])
    '[Schöne]{lang="de"} World'
"""

from __future__ import annotations

import re
from typing import Any, Final

from kokorog2p.ssmd import ANNOTATION_REGEX

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


def preprocess_multilang(
    text: str,
    default_language: str = "en-us",
    allowed_languages: list[str] | None = None,
    confidence_threshold: float = 0.7,
) -> str:
    """Annotate detected non-default words with SSMD language tags.

    Args:
        text: Input text to annotate.
        default_language: Base language for unmarked words.
        allowed_languages: Language codes to detect (must include default_language).
        confidence_threshold: Minimum confidence (0.0-1.0) to accept detection.

    Returns:
        Text with SSMD {lang="..."} annotations for detected words.

    Raises:
        ImportError: If lingua-language-detector is not installed.
        ValueError: If allowed_languages is missing or default_language not allowed.
    """
    if not LINGUA_AVAILABLE:
        raise ImportError(
            "lingua-language-detector is required for preprocess_multilang. "
            "Install with: pip install lingua-language-detector"
        )

    if allowed_languages is None or len(allowed_languages) == 0:
        raise ValueError("allowed_languages must be specified and non-empty")

    normalized_allowed = [_normalize_language(lang) for lang in allowed_languages]
    normalized_default = _normalize_language(default_language)
    if normalized_default not in normalized_allowed:
        raise ValueError("default_language must be in allowed_languages")

    lingua_languages = _map_to_lingua_languages(normalized_allowed)
    if not lingua_languages:
        raise ValueError("allowed_languages do not map to lingua languages")

    detector = (
        LanguageDetectorBuilder.from_languages(*lingua_languages)  # type: ignore
        .with_preloaded_language_models()
        .build()
    )

    cache: dict[str, str] = {}

    def detect_language(word: str) -> str:
        if len(word) < 3 or not any(c.isalnum() for c in word):
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

    def process_plain_segment(segment: str) -> str:
        parts: list[str] = []
        for token in WORD_OR_PUNCT_REGEX.findall(segment):
            if token.isspace():
                parts.append(token)
                continue
            if token.isalnum() or any(ch.isalnum() for ch in token):
                detected = detect_language(token)
                if detected != normalized_default:
                    parts.append(f'[{token}]{{lang="{detected}"}}')
                else:
                    parts.append(token)
            else:
                parts.append(token)
        return "".join(parts)

    result: list[str] = []
    last_end = 0
    for match in ANNOTATION_REGEX.finditer(text):
        result.append(process_plain_segment(text[last_end : match.start()]))
        result.append(match.group(0))
        last_end = match.end()

    if last_end < len(text):
        result.append(process_plain_segment(text[last_end:]))

    return "".join(result)


__all__ = ["preprocess_multilang"]
