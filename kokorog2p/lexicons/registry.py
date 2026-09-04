"""Manifest-generated named lexicon registry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from ._generated_registry import GENERATED_LEXICONS


@dataclass(frozen=True, slots=True)
class LexiconSpec:
    language: str
    name: str
    resource: str | None
    kind: Literal["pronunciation", "membership"]
    rating: int | None
    case_aliases: bool
    phoneme_encoding: str
    metadata: Mapping[str, object]
    id: str
    default_priority: int | None
    backend: str | None = None


_SPECS: tuple[LexiconSpec, ...] = tuple(
    LexiconSpec(
        language=str(record["language"]),
        name=str(record["name"]),
        resource=str(record["resource"]),
        kind=record["kind"],
        rating=record.get("rating"),
        case_aliases=bool(record["case_aliases"]),
        phoneme_encoding=str(record["phoneme_encoding"]),
        metadata=MappingProxyType(dict(record)),
        id=str(record["id"]),
        default_priority=record.get("default_priority"),
    )
    for record in GENERATED_LEXICONS
)

_EXTERNAL_SPECS: tuple[LexiconSpec, ...] = (
    LexiconSpec(
        language="de-de",
        name="gold",
        resource=None,
        kind="pronunciation",
        rating=4,
        case_aliases=False,
        phoneme_encoding="ipa",
        metadata=MappingProxyType(
            {"id": "de-de:gold", "language": "de-de", "name": "gold"}
        ),
        id="de-de:gold",
        default_priority=10,
        backend="lexphon",
    ),
    LexiconSpec(
        language="de-de",
        name="crane",
        resource=None,
        kind="pronunciation",
        rating=None,
        case_aliases=False,
        phoneme_encoding="ipa",
        metadata=MappingProxyType(
            {"id": "de-de:crane", "language": "de-de", "name": "crane"}
        ),
        id="de-de:crane",
        default_priority=None,
        backend="lexphon",
    ),
    LexiconSpec(
        language="de-de",
        name="espeak",
        resource=None,
        kind="pronunciation",
        rating=None,
        case_aliases=False,
        phoneme_encoding="ipa",
        metadata=MappingProxyType(
            {"id": "de-de:espeak", "language": "de-de", "name": "espeak"}
        ),
        id="de-de:espeak",
        default_priority=None,
        backend="lexphon",
    ),
    LexiconSpec(
        language="de-de",
        name="olaph",
        resource=None,
        kind="pronunciation",
        rating=None,
        case_aliases=False,
        phoneme_encoding="ipa",
        metadata=MappingProxyType(
            {"id": "de-de:olaph", "language": "de-de", "name": "olaph"}
        ),
        id="de-de:olaph",
        default_priority=None,
        backend="lexphon",
    ),
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
    "sv": "sv-se",
    "swe": "sv-se",
    "swedish": "sv-se",
}


def normalize_language(language: str) -> str:
    """Normalize supported lexicon language aliases to registry languages."""
    normalized = language.lower().replace("_", "-")
    return _LANGUAGE_ALIASES.get(normalized, normalized)


def _specs_for(language: str) -> tuple[LexiconSpec, ...]:
    canonical = normalize_language(language)
    specs = tuple(spec for spec in _SPECS if spec.language == canonical)
    if canonical == "de-de":
        return _EXTERNAL_SPECS
    return specs


def available_lexicons(language: str) -> tuple[str, ...]:
    """Return all registered lexicon names in manifest order."""
    return tuple(spec.name for spec in _specs_for(language))


def get_lexicon_spec(language: str, name: str) -> LexiconSpec:
    """Return metadata for one named lexicon or raise an actionable error."""
    specs = _specs_for(language)
    for spec in specs:
        if spec.name == name:
            return spec
    valid = ", ".join(spec.name for spec in specs) or "none"
    raise ValueError(
        f"Unknown lexicon {name!r} for language {language!r}; valid names: {valid}"
    )


def _legacy_enabled(spec: LexiconSpec, *, load_gold: bool, load_silver: bool) -> bool:
    if spec.name == "gold":
        return load_gold
    if spec.name == "silver":
        return load_silver
    return True


def normalize_lexicon_selection(
    language: str,
    lexicons: str | Sequence[str] | None,
    *,
    load_gold: bool | None = None,
    load_silver: bool | None = None,
) -> tuple[str, ...]:
    """Normalize explicit selections and backwards-compatible legacy flags."""
    canonical = normalize_language(language)
    specs = _specs_for(canonical)
    if lexicons is None:
        gold = True if load_gold is None else load_gold
        silver = True if load_silver is None else load_silver
        selected = [
            spec
            for spec in specs
            if spec.default_priority is not None
            and _legacy_enabled(spec, load_gold=gold, load_silver=silver)
        ]
        selected.sort(key=lambda spec: (spec.default_priority, specs.index(spec)))
        return tuple(spec.name for spec in selected)

    names = (lexicons,) if isinstance(lexicons, str) else tuple(lexicons)
    if len(names) != len(set(names)):
        raise ValueError("lexicons selection must not contain duplicate names")
    for name in names:
        get_lexicon_spec(canonical, name)
    # Explicit selections are the new, more precise API. Legacy flags are
    # intentionally ignored here because integrations may continue to pass
    # their old defaults alongside a named selection.
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
            "resource": spec.resource,
            "kind": spec.kind,
            "rating": spec.rating,
            "case_aliases": spec.case_aliases,
            "phoneme_encoding": spec.phoneme_encoding,
            "default_priority": spec.default_priority,
            "backend": spec.backend,
        }
    )


def iter_lexicon_specs() -> tuple[LexiconSpec, ...]:
    """Return all registry specifications in generated manifest order."""
    return _SPECS


__all__ = [
    "LexiconSpec",
    "available_lexicons",
    "get_lexicon_spec",
    "iter_lexicon_specs",
    "lexicon_info",
    "normalize_language",
    "normalize_lexicon_selection",
]
