"""Explicit derived pronunciation views used only for comparison."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping

VIEW_VERSION = "1"

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


def _replace_longest(value: str) -> str:
    for source in sorted(_REPLACEMENTS, key=len, reverse=True):
        value = value.replace(source, _REPLACEMENTS[source])
    return value


def to_kokoro_view(
    source_id: str, ipa: str, *, vocab: Mapping[str, int] | None = None
) -> str:
    """Return a derived view; raw source records are never modified."""
    if source_id == "gruut_espeak":
        return ipa.replace(" ", "")
    if source_id == "crane_wiktionary":
        value = _replace_longest(unicodedata.normalize("NFC", ipa))
        if vocab is not None:
            value = "".join(
                char if char.isspace() else char
                for char in value
                if char.isspace() or char in vocab
            )
            return " ".join(value.split())
        return " ".join(value.split())
    return ipa


def view_variants(
    source_id: str, variants: tuple[str, ...], *, vocab: Mapping[str, int] | None = None
) -> tuple[str, ...]:
    return tuple(to_kokoro_view(source_id, value, vocab=vocab) for value in variants)
