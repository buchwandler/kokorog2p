"""Named packaged lexicon registry."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class LexiconSpec:
    language: str
    name: str
    resource: str
    kind: Literal["pronunciation", "membership"]
    rating: int | None
    case_aliases: bool
    phoneme_encoding: str
    metadata: Mapping[str, object]


_SPECS: tuple[LexiconSpec, ...] = (
    LexiconSpec(
        "en-us",
        "gold",
        "en_us_gold.g2lex",
        "pronunciation",
        4,
        True,
        "kokoro-v1",
        {"id": "en-us:gold"},
    ),
    LexiconSpec(
        "en-us",
        "silver",
        "en_us_silver.g2lex",
        "pronunciation",
        3,
        True,
        "kokoro-v1",
        {"id": "en-us:silver"},
    ),
    LexiconSpec(
        "en-gb",
        "gold",
        "en_gb_gold.g2lex",
        "pronunciation",
        4,
        True,
        "kokoro-v1",
        {"id": "en-gb:gold"},
    ),
    LexiconSpec(
        "en-gb",
        "silver",
        "en_gb_silver.g2lex",
        "pronunciation",
        3,
        True,
        "kokoro-v1",
        {"id": "en-gb:silver"},
    ),
    LexiconSpec(
        "de-de",
        "gold",
        "de_gold.g2lex",
        "pronunciation",
        4,
        False,
        "ipa",
        {"id": "de-de:gold"},
    ),
    LexiconSpec(
        "fr-fr",
        "gold",
        "fr_gold.g2lex",
        "pronunciation",
        4,
        True,
        "kokoro-v1",
        {"id": "fr-fr:gold"},
    ),
    LexiconSpec(
        "ja-jp",
        "words",
        "ja_words.g2lex",
        "membership",
        None,
        False,
        "none",
        {"id": "ja-jp:words"},
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
}


def normalize_language(language: str) -> str:
    """Normalize supported lexicon language aliases to registry languages."""
    normalized = language.lower().replace("_", "-")
    return _LANGUAGE_ALIASES.get(normalized, normalized)


def _specs_for(language: str) -> tuple[LexiconSpec, ...]:
    canonical = normalize_language(language)
    return tuple(spec for spec in _SPECS if spec.language == canonical)


def available_lexicons(language: str) -> tuple[str, ...]:
    """Return registered lexicon names in deterministic precedence order."""
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


def normalize_lexicon_selection(
    language: str,
    lexicons: str | Sequence[str] | None,
    *,
    load_gold: bool = True,
    load_silver: bool = True,
) -> tuple[str, ...]:
    """Normalize an explicit or legacy lexicon selection."""
    canonical = normalize_language(language)
    available = available_lexicons(canonical)
    if lexicons is None:
        if canonical.startswith("en-"):
            return (
                ("gold", "silver")
                if load_gold and load_silver
                else ("gold",)
                if load_gold
                else ("silver",)
                if load_silver
                else ()
            )
        if "gold" in available:
            return ("gold",) if load_gold else ()
        if "words" in available:
            return ("words",) if load_gold else ()
        return ()
    names = (lexicons,) if isinstance(lexicons, str) else tuple(lexicons)
    if len(names) != len(set(names)):
        raise ValueError("lexicons selection must not contain duplicate names")
    for name in names:
        get_lexicon_spec(canonical, name)
    if (load_gold, load_silver) != (True, True):
        expected = ("gold" in names, "silver" in names)
        if (load_gold, load_silver) != expected:
            raise ValueError(
                "Explicit lexicons selection contradicts load_gold/load_silver: "
                f"selection={names!r}, flags={(load_gold, load_silver)!r}"
            )
    return names


def iter_lexicon_specs() -> tuple[LexiconSpec, ...]:
    """Return all registry specifications in manifest order."""
    return _SPECS


__all__ = [
    "LexiconSpec",
    "available_lexicons",
    "get_lexicon_spec",
    "iter_lexicon_specs",
    "normalize_language",
    "normalize_lexicon_selection",
]
