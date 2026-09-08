"""Immutable evidence returned by selected lexical resources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from kokorog2p.language_codes import normalize_language_code


@dataclass(frozen=True, slots=True)
class LexiconEvidence:
    """Positive membership evidence from an explicitly selected lexical layer."""

    language: str
    lexicon_id: str
    pronunciation: str | None
    kind: Literal["pronunciation", "membership"]
    lexicon_name: str | None = None
    rating: int | None = None
    phoneme_encoding: str | None = None
    metadata: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", normalize_language_code(self.language))
        if self.metadata is not None:
            object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def as_dict(self) -> dict[str, object]:
        """Return a JSON-compatible diagnostic representation."""
        return {
            "language": self.language,
            "lexicon_id": self.lexicon_id,
            "pronunciation": self.pronunciation,
            "kind": self.kind,
            "lexicon_name": self.lexicon_name,
            "rating": self.rating,
            "phoneme_encoding": self.phoneme_encoding,
            "metadata": None if self.metadata is None else dict(self.metadata),
        }


def _selected_lexphon_layers(
    language: str, selected_lexicons: Sequence[str]
) -> tuple[tuple[str, str], ...]:
    """Resolve selected Lexphon names or IDs to stable ``(id, name)`` pairs."""
    from kokorog2p.lexicons.registry import get_lexicon_spec

    layers: list[tuple[str, str]] = []
    for selected in selected_lexicons:
        value = str(selected)
        if ":" in value:
            layers.append((value, value.rsplit(":", 1)[-1]))
            continue
        try:
            spec = get_lexicon_spec(language, value)
        except ValueError:
            continue
        layers.append((spec.id, spec.name))
    return tuple(layers)


def _variant_metadata(token: object) -> tuple[dict[str, object], ...]:
    variants = getattr(token, "variants", ())
    return tuple(
        {
            "pronunciation": variant.pronunciation,
            "source_pronunciation": variant.source_pronunciation,
            "language_markers": [
                {"language": marker.language, "ipa_offset": marker.ipa_offset}
                for marker in variant.language_markers
            ],
        }
        for variant in variants
    )


def evidence_from_lexphon_token(
    *,
    language: str,
    token: object | None,
    selected_lexicons: Sequence[str],
) -> LexiconEvidence | None:
    """Convert a known selected Lexphon lexical token into evidence."""
    if token is None or getattr(token, "source", None) != "lexicon":
        return None
    if not bool(getattr(token, "known", False)):
        return None

    layers = _selected_lexphon_layers(language, selected_lexicons)
    if not layers:
        return None
    layer_by_id = {lexicon_id: name for lexicon_id, name in layers}
    lexicon_id = getattr(token, "lexicon_id", None)
    if lexicon_id is None or str(lexicon_id) not in layer_by_id:
        return None
    lexicon_id = str(lexicon_id)
    lexicon_name = layer_by_id[lexicon_id]

    from kokorog2p.lexicons.registry import get_lexicon_spec

    try:
        spec = get_lexicon_spec(language, lexicon_name)
    except ValueError:
        spec = None

    variants = _variant_metadata(token)
    primary = variants[0] if variants else None
    pronunciation = getattr(token, "pronunciation", None)
    metadata = {
        "source": "lexicon",
        "matched_key": getattr(token, "matched_key", None),
        "selector_tag": getattr(token, "selector_tag", None),
        "variants": list(variants),
        "source_encoding": getattr(token, "source_encoding", None),
        "source_pronunciation": (
            None if primary is None else primary["source_pronunciation"]
        ),
        "pronunciation_language_markers": (
            [] if primary is None else primary["language_markers"]
        ),
    }
    return LexiconEvidence(
        language=language,
        lexicon_id=lexicon_id,
        pronunciation=pronunciation,
        kind="pronunciation" if pronunciation is not None else "membership",
        lexicon_name=lexicon_name,
        rating=None if spec is None else spec.rating,
        phoneme_encoding="ipa",
        metadata=metadata,
    )


__all__ = ["LexiconEvidence", "evidence_from_lexphon_token"]
