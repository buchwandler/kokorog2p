"""Canonical language-code normalization shared by the factory and routing."""

from __future__ import annotations

_LANGUAGE_ALIASES: dict[str, str] = {
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
    "ar": "ar",
    "ara": "ar",
    "arabic": "ar",
    "ar-msa": "ar",
    "msa": "ar",
    "ar-sa": "ar",
    "sv": "sv-se",
    "sv-se": "sv-se",
    "swe": "sv-se",
    "swedish": "sv-se",
    "th": "th-th",
    "th-th": "th-th",
    "tha": "th-th",
    "thai": "th-th",
    "ru": "ru-ru",
    "ru-ru": "ru-ru",
    "rus": "ru-ru",
    "russian": "ru-ru",
    "kk": "kk",
    "kk-kz": "kk",
    "kaz": "kk",
    "kazakh": "kk",
}


def normalize_language_code(language: str) -> str:
    """Return the canonical factory language code for an alias."""
    if not isinstance(language, str) or not language.strip():
        raise ValueError("language must be a non-empty string")
    normalized = language.strip().lower().replace("_", "-")
    return _LANGUAGE_ALIASES.get(normalized, normalized)


__all__ = ["normalize_language_code"]
