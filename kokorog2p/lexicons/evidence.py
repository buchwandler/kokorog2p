"""Immutable evidence returned by selected lexical resources."""

from __future__ import annotations

from collections.abc import Mapping
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


__all__ = ["LexiconEvidence"]
