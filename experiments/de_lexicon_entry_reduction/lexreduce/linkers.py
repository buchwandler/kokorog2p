"""Bounded shared German linker definitions and spelling search."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Linker:
    spelling: str
    pronunciation: tuple[str, ...] = ("",)
    version: str = "1"

    def as_dict(self) -> dict[str, Any]:
        return {
            "spelling": self.spelling,
            "pronunciation": list(self.pronunciation),
            "version": self.version,
        }


@dataclass(frozen=True, slots=True)
class LinkerCandidate:
    left: str
    linker: Linker
    right: str

    @property
    def components(self) -> tuple[str, str, str]:
        return self.left, self.linker.spelling, self.right


@dataclass(frozen=True, slots=True)
class LinkerTable:
    """A small global table. It never stores a word-specific linker choice."""

    linkers: tuple[Linker, ...]
    max_candidates: int = 32

    def candidates(
        self, word: str, literals: Mapping[str, object]
    ) -> tuple[LinkerCandidate, ...]:
        found: list[LinkerCandidate] = []
        for linker in self.linkers:
            start = 1
            while True:
                position = word.find(linker.spelling, start)
                if position < 0:
                    break
                left, right = word[:position], word[position + len(linker.spelling) :]
                if left in literals and right in literals and left and right:
                    found.append(LinkerCandidate(left, linker, right))
                start = position + 1
        found.sort(
            key=lambda item: (
                -len(item.left),
                item.left,
                item.linker.spelling,
                item.right,
            )
        )
        return tuple(found[: self.max_candidates])

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": "1",
            "max_candidates": self.max_candidates,
            "linkers": [linker.as_dict() for linker in self.linkers],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> LinkerTable:
        return cls(
            tuple(
                Linker(
                    str(item["spelling"]),
                    tuple(str(value) for value in item.get("pronunciation", [""])),
                    str(item.get("version", "1")),
                )
                for item in value.get("linkers", ())
            ),
            int(value.get("max_candidates", 32)),
        )


def german_linker_table(*, max_candidates: int = 32) -> LinkerTable:
    """Return the bounded initial German Fugenelement inventory."""
    return LinkerTable(
        tuple(
            Linker(spelling) for spelling in ("s", "es", "n", "en", "e", "er", "ens")
        ),
        max_candidates=max_candidates,
    )
