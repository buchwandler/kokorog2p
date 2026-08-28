"""Compact indexes over the retained literal spelling basis."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(slots=True)
class MutableLiteralPrefixIndex:
    """Builder index storing only lengths grouped by first character."""

    lengths_by_initial: dict[str, set[int]]

    @classmethod
    def empty(cls) -> MutableLiteralPrefixIndex:
        return cls({})

    def add(self, word: str) -> None:
        if not word:
            return
        self.lengths_by_initial.setdefault(word[0], set()).add(len(word))

    def freeze(self) -> LiteralPrefixIndex:
        return LiteralPrefixIndex.from_lengths(self.lengths_by_initial)

    def prefixes(
        self,
        word: str,
        position: int,
        literals: Mapping[str, object],
    ) -> tuple[str, ...]:
        if position >= len(word):
            return ()
        lengths = sorted(self.lengths_by_initial.get(word[position], ()))
        return tuple(
            word[position : position + length]
            for length in lengths
            if position + length <= len(word)
            and word[position : position + length] in literals
        )


@dataclass(frozen=True, slots=True)
class LiteralPrefixIndex:
    """Immutable prefix-length index backed by tuples, not trie node objects."""

    lengths_by_initial: tuple[tuple[str, tuple[int, ...]], ...]

    @classmethod
    def from_literals(cls, literals: Mapping[str, object]) -> LiteralPrefixIndex:
        mutable = MutableLiteralPrefixIndex.empty()
        for word in literals:
            mutable.add(word)
        return mutable.freeze()

    @classmethod
    def from_lengths(cls, lengths: Mapping[str, Iterable[int]]) -> LiteralPrefixIndex:
        return cls(
            tuple(
                (initial, tuple(sorted(set(values))))
                for initial, values in sorted(lengths.items())
            )
        )

    def _lengths(self, initial: str) -> tuple[int, ...]:
        for key, values in self.lengths_by_initial:
            if key == initial:
                return values
        return ()

    def prefixes(
        self,
        word: str,
        position: int,
        literals: Mapping[str, object],
    ) -> tuple[str, ...]:
        if position >= len(word):
            return ()
        return tuple(
            word[position : position + length]
            for length in self._lengths(word[position])
            if position + length <= len(word)
            and word[position : position + length] in literals
        )

    @property
    def state_count(self) -> int:
        return sum(len(values) for _, values in self.lengths_by_initial)

    @property
    def edge_count(self) -> int:
        return sum(length for _, values in self.lengths_by_initial for length in values)

    def as_dict(self) -> dict[str, list[int]]:
        return {initial: list(values) for initial, values in self.lengths_by_initial}

    @classmethod
    def from_dict(cls, value: Mapping[str, Iterable[int]]) -> LiteralPrefixIndex:
        return cls.from_lengths(value)
