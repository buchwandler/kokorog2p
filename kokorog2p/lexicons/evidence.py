"""Immutable evidence returned by selected lexical resources."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from kokorog2p.language_codes import normalize_language_code


@dataclass(frozen=True, slots=True)
class LexiconEvidence:
    """Positive membership evidence from an explicitly selected lexical layer.

    A hit proves membership in the named selected resource. It does not prove
    exclusive ownership of the spelling by this language.
    """

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


def evidence_from_lexphon_token(
    *,
    language: str,
    token: object | None,
    selected_lexicons: Sequence[str],
) -> LexiconEvidence | None:
    """Convert a known token from selected Lexphon layers into evidence.

    A token without a source identity is accepted only when the selected stack
    has exactly one resolvable layer. No pronunciation fallback is attempted.
    """
    if token is None or not bool(getattr(token, "known", False)):
        return None

    layers = _selected_lexphon_layers(language, selected_lexicons)
    if not layers:
        return None
    layer_by_id = {lexicon_id: name for lexicon_id, name in layers}
    layer_by_name = {name: lexicon_id for lexicon_id, name in layers}
    token_id = getattr(token, "lexicon_id", None)
    if token_id is not None:
        lexicon_id = str(token_id)
        if lexicon_id not in layer_by_id:
            return None
        lexicon_name = layer_by_id[lexicon_id]
    else:
        source = str(getattr(token, "source", "") or "")
        source_id = layer_by_name.get(source) or (
            source if source in layer_by_id else None
        )
        if source_id is not None:
            lexicon_id = source_id
            lexicon_name = layer_by_id[lexicon_id]
        elif len(layers) == 1:
            lexicon_id, lexicon_name = layers[0]
        else:
            return None

    from kokorog2p.lexicons.registry import get_lexicon_spec

    try:
        spec = get_lexicon_spec(language, lexicon_name)
    except ValueError:
        spec = None
    rating = None if spec is None else spec.rating
    phoneme_encoding = getattr(token, "alphabet", None) or (
        None if spec is None else spec.phoneme_encoding
    )
    pronunciation = getattr(token, "pronunciation", None)
    metadata = {
        "source": getattr(token, "source", None),
        "matched_key": getattr(token, "matched_key", None),
        "selector_tag": getattr(token, "selector_tag", None),
        "variants": getattr(token, "variants", ()),
        "alphabet": getattr(token, "alphabet", None),
        "source_encoding": getattr(token, "source_encoding", None),
    }
    return LexiconEvidence(
        language=language,
        lexicon_id=lexicon_id,
        pronunciation=pronunciation,
        kind="pronunciation" if pronunciation is not None else "membership",
        lexicon_name=lexicon_name,
        rating=rating,
        phoneme_encoding=phoneme_encoding,
        metadata=metadata,
    )


__all__ = ["LexiconEvidence", "evidence_from_lexphon_token"]
