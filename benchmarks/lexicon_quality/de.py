"""Kokoro-specific German pronunciation rendering for quality benchmarks."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping

_REPLACEMENTS = {
    "t͡s": "ʦ",
    "d͡z": "ʣ",
    "ts": "ʦ",
    "dz": "ʣ",
    "aʊ̯": "W",
    "aɪ̯": "I",
    "ɔʏ̯": "ɔy",
    "aʊ": "W",
    "aɪ": "I",
    "ʏ": "y",
    "n̩": "n",
    "l̩": "l",
}


def to_kokoro_view(
    source_id: str, pronunciation: str, *, vocab: Mapping[str, int] | None = None
) -> str:
    """Convert a raw source pronunciation for Kokoro comparison only."""
    if source_id == "gruut_espeak":
        return pronunciation.replace(" ", "")
    if source_id == "crane_wiktionary":
        value = unicodedata.normalize("NFC", pronunciation)
        for source in sorted(_REPLACEMENTS, key=len, reverse=True):
            value = value.replace(source, _REPLACEMENTS[source])
        if vocab is not None:
            value = "".join(char for char in value if char.isspace() or char in vocab)
        return " ".join(value.split())
    return pronunciation


def view_variants(
    source_id: str, variants: tuple[str, ...], *, vocab: Mapping[str, int] | None = None
) -> tuple[str, ...]:
    return tuple(to_kokoro_view(source_id, value, vocab=vocab) for value in variants)


__all__ = ["to_kokoro_view", "view_variants"]
