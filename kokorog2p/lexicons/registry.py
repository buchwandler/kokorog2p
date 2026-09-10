"""Runtime metadata for externally provisioned lexicons."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class LexiconSpec:
    language: str
    name: str
    kind: str
    rating: int | None
    phoneme_encoding: str
    metadata: Mapping[str, object]
    id: str
    default_priority: int | None
    backend: str


def _external_spec(
    language: str,
    name: str,
    *,
    external_language: str | None = None,
    rating: int | None = 5,
    default_priority: int | None = 10,
    backend: str = "lexphon",
    kind: str = "pronunciation",
    phoneme_encoding: str = "ipa",
) -> LexiconSpec:
    identifier = f"{external_language or language}:{name}"
    return LexiconSpec(
        language=language,
        name=name,
        kind=kind,
        rating=rating,
        phoneme_encoding=phoneme_encoding,
        metadata=MappingProxyType(
            {
                "id": identifier,
                "language": language,
                "name": name,
                "backend": backend,
            }
        ),
        id=identifier,
        default_priority=default_priority,
        backend=backend,
    )


_EXTERNAL_SPECS_BY_LANGUAGE: dict[str, tuple[LexiconSpec, ...]] = {
    "en-us": (_external_spec("en-us", "gold", rating=4, phoneme_encoding="kokoro-v1"),),
    "en-gb": (_external_spec("en-gb", "gold", rating=4, phoneme_encoding="kokoro-v1"),),
    "fr-fr": (_external_spec("fr-fr", "gold", rating=4, phoneme_encoding="kokoro-v1"),),
    "de-de": (
        _external_spec("de-de", "gold", rating=4),
        _external_spec("de-de", "crane", rating=None, default_priority=None),
        _external_spec("de-de", "espeak", rating=None, default_priority=None),
        _external_spec("de-de", "olaph", rating=None, default_priority=None),
        _external_spec("de-de", "lexhint", rating=None, default_priority=None),
    ),
    "sv-se": (_external_spec("sv-se", "nst", rating=None, default_priority=None),),
    "ru-ru": (_external_spec("ru-ru", "lexhint", external_language="ru"),),
    "th-th": (_external_spec("th-th", "lexhint", external_language="th"),),
    "vi-vn": (_external_spec("vi-vn", "lexhint", external_language="vi"),),
    "ja-jp": (_external_spec("ja-jp", "lexhint", external_language="ja"),),
    "ko-kr": (_external_spec("ko-kr", "lexhint", external_language="ko"),),
    "pt-br": (_external_spec("pt-br", "lexhint", external_language="pt"),),
    "pt-pt": (_external_spec("pt-pt", "lexhint", external_language="pt"),),
}

_EXTERNAL_SPECS: tuple[LexiconSpec, ...] = tuple(
    spec for specs in _EXTERNAL_SPECS_BY_LANGUAGE.values() for spec in specs
)

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
    "ja": "ja-jp",
    "jpn": "ja-jp",
    "japanese": "ja-jp",
    "ko": "ko-kr",
    "kor": "ko-kr",
    "korean": "ko-kr",
    "pt": "pt-br",
    "por": "pt-br",
    "portuguese": "pt-br",
    "ru": "ru-ru",
    "rus": "ru-ru",
    "russian": "ru-ru",
    "th": "th-th",
    "tha": "th-th",
    "thai": "th-th",
    "vi": "vi-vn",
    "vie": "vi-vn",
    "vietnamese": "vi-vn",
    "sv": "sv-se",
    "swe": "sv-se",
    "swedish": "sv-se",
}


def normalize_language(language: str) -> str:
    """Normalize supported lexicon language aliases to registry languages."""
    normalized = language.lower().replace("_", "-")
    return _LANGUAGE_ALIASES.get(normalized, normalized)


def _specs_for(language: str) -> tuple[LexiconSpec, ...]:
    return _EXTERNAL_SPECS_BY_LANGUAGE.get(normalize_language(language), ())


def available_lexicons(language: str) -> tuple[str, ...]:
    """Return all registered lexicon names in registry order."""
    return tuple(spec.name for spec in _specs_for(language))


def get_lexicon_spec(language: str, name: str) -> LexiconSpec:
    """Return metadata for one named lexicon or raise an actionable error."""
    specs = _specs_for(language)
    for spec in specs:
        if spec.name == name:
            return spec
    valid = ", ".join(spec.name for spec in specs) or "none"
    raise ValueError(
        f"Unknown lexicon {name!r} for {normalize_language(language)}. "
        f"Available lexicons: {valid}"
    )


def normalize_lexicon_selection(
    language: str,
    lexicons: str | Sequence[str] | None,
) -> tuple[str, ...]:
    """Normalize an explicit selection or return the language default."""
    canonical = normalize_language(language)
    specs = _specs_for(canonical)
    if lexicons is None:
        selected = [spec for spec in specs if spec.default_priority is not None]
        selected.sort(key=lambda spec: (spec.default_priority, specs.index(spec)))
        return tuple(spec.name for spec in selected)

    names = (lexicons,) if isinstance(lexicons, str) else tuple(lexicons)
    if len(names) != len(set(names)):
        raise ValueError("lexicons selection must not contain duplicate names")
    for name in names:
        get_lexicon_spec(canonical, name)
    return names


def lexicon_info(language: str, name: str) -> Mapping[str, object]:
    """Return immutable public metadata for a named lexicon."""
    spec = get_lexicon_spec(language, name)
    return MappingProxyType(
        {
            **dict(spec.metadata),
            "id": spec.id,
            "language": spec.language,
            "name": spec.name,
            "kind": spec.kind,
            "rating": spec.rating,
            "phoneme_encoding": spec.phoneme_encoding,
            "default_priority": spec.default_priority,
            "backend": spec.backend,
        }
    )


def iter_lexicon_specs() -> tuple[LexiconSpec, ...]:
    """Return all runtime registry specifications."""
    return _EXTERNAL_SPECS


__all__ = [
    "LexiconSpec",
    "available_lexicons",
    "get_lexicon_spec",
    "iter_lexicon_specs",
    "lexicon_info",
    "normalize_language",
    "normalize_lexicon_selection",
]
