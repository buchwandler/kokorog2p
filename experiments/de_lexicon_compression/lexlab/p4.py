"""Opt-in P4 linker candidates and front-coded word-index prototype."""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import product
from typing import Any

from .compact import _bytes, _common, _source
from .decoder import CompressedLexicon
from .model import SourceInfo

DEFAULT_LINKERS = ("s", "n", "en", "e", "er")


def exact_linker_candidates(
    word: str,
    expected: tuple[str, ...],
    atoms: dict[str, tuple[str, ...]],
    *,
    linkers: tuple[str, ...] = DEFAULT_LINKERS,
    max_candidates: int = 100,
) -> tuple[tuple[str, ...], ...]:
    """Generate only exact linker shapes; approximation is never accepted."""
    found = []
    for linker in linkers:
        start = 1
        while True:
            position = word.find(linker, start)
            if position < 1 or position + len(linker) >= len(word):
                break
            left = word[:position]
            right = word[position + len(linker) :]
            if left not in atoms or linker not in atoms or right not in atoms:
                start = position + 1
                continue
            values = [atoms[left], atoms[linker], atoms[right]]
            candidate = tuple("".join(parts) for parts in product(*values))
            if candidate == expected:
                found.append((left, linker, right))
                if len(found) >= max_candidates:
                    return tuple(found)
            start = position + 1
    return tuple(found)


def front_encode(words: tuple[str, ...], *, block_size: int = 16) -> list[list[object]]:
    """Encode sorted words as (shared-prefix length, UTF-8-safe suffix)."""
    encoded: list[list[object]] = []
    previous = ""
    for index, word in enumerate(words):
        if index % block_size == 0:
            prefix = 0
        else:
            prefix = 0
            for left, right in zip(previous, word, strict=False):
                if left != right:
                    break
                prefix += 1
        encoded.append([prefix, word[prefix:]])
        previous = word
    return encoded


def front_decode(
    encoded: list[list[object]], *, block_size: int = 16
) -> tuple[str, ...]:
    words = []
    previous = ""
    for index, (prefix, suffix) in enumerate(encoded):
        if index % block_size == 0 and int(prefix) != 0:
            raise ValueError("front-coded block must start with zero prefix")
        word = previous[: int(prefix)] + str(suffix)
        words.append(word)
        previous = word
    return tuple(words)


@dataclass(slots=True)
class FrontCodedLexicon:
    source: SourceInfo
    word_index: tuple[str, ...]
    entries: dict[str, tuple[str, ...]]
    derived: dict[str, tuple[str, ...]]
    atoms: dict[str, tuple[str, ...]]
    metadata: dict[str, object]

    def lookup_all(self, word: str) -> tuple[str, ...]:
        if word in self.entries:
            return self.entries[word]
        components = self.derived.get(word)
        if components is None:
            return ()
        result = [""]
        for component in components:
            result = [
                prefix + value for prefix in result for value in self.atoms[component]
            ]
        return tuple(result)

    @property
    def words(self) -> tuple[str, ...]:
        return self.word_index


def to_front_coded_asset(compressed: CompressedLexicon) -> FrontCodedLexicon:
    words = tuple(
        sorted((*compressed.atoms, *compressed.exceptions, *compressed.derived))
    )
    return FrontCodedLexicon(
        compressed.source,
        words,
        dict(compressed.exceptions) | dict(compressed.atoms),
        dict(compressed.derived),
        dict(compressed.atoms),
        {**compressed.metadata, "mode": "front-coded"},
    )


def front_coded_asset_dict(compressed: CompressedLexicon) -> dict[str, Any]:
    asset = to_front_coded_asset(compressed)
    return {
        **_common(compressed, "front-coded"),
        "block_size": 16,
        "word_index": front_encode(asset.word_index),
        "entries": {word: list(values) for word, values in asset.entries.items()},
        "atoms": {word: list(values) for word, values in asset.atoms.items()},
        "derived": {word: list(values) for word, values in asset.derived.items()},
    }


def serialize_front_coded(compressed: CompressedLexicon) -> bytes:
    return _bytes(front_coded_asset_dict(compressed))


def deserialize_front_coded(data: bytes) -> FrontCodedLexicon:
    value = json.loads(data.decode("utf-8"))
    if value.get("schema") != 2 or value.get("mode") != "front-coded":
        raise ValueError("not a front-coded asset")
    block_size = int(value.get("block_size", 16))
    return FrontCodedLexicon(
        _source(value["source"]),
        front_decode(value.get("word_index", []), block_size=block_size),
        {word: tuple(values) for word, values in value.get("entries", {}).items()},
        {word: tuple(values) for word, values in value.get("derived", {}).items()},
        {word: tuple(values) for word, values in value.get("atoms", {}).items()},
        dict(value.get("metadata", {})),
    )
