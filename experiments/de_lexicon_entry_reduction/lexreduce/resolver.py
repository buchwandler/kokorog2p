"""Ephemeral literal-or-recursive constituent resolution for V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .composer import SearchLimitError, segmentation_rank


@dataclass(slots=True)
class ResolveContext:
    memo: dict[str, tuple[str, ...] | None] = field(default_factory=dict)
    stack: set[str] = field(default_factory=set)
    depth: int = 0
    states: int = 0


@dataclass(slots=True)
class ComponentResolver:
    """Resolve literals or known words by strict proper-substring recursion."""

    membership: Any
    composer: Any
    literals: Any
    prefix_index: Any
    max_depth: int = 4
    max_states: int = 100_000
    _lengths: dict[str, tuple[int, ...]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        lengths: dict[str, set[int]] = {}
        for word in self.membership.iter_words():
            if word:
                lengths.setdefault(word[0], set()).add(len(word))
        self._lengths = {key: tuple(sorted(value)) for key, value in lengths.items()}

    def resolve(
        self, word: str, context: ResolveContext | None = None
    ) -> tuple[str, ...] | None:
        context = context or ResolveContext()
        literal = self.literals.get(word)
        if literal is not None:
            return literal
        if not word or not self.membership.contains(word):
            return None
        if word in context.memo:
            return context.memo[word]
        if word in context.stack or context.depth >= self.max_depth:
            return None
        context.states += 1
        if context.states > self.max_states:
            raise SearchLimitError(
                f"recursive search limit {self.max_states} reached for {word!r}"
            )
        context.stack.add(word)
        context.depth += 1
        try:
            result = self.composer.derive_result(
                word,
                literals=self.literals,
                prefix_index=self.prefix_index,
                resolver=self,
                context=context,
            )
        finally:
            context.depth -= 1
            context.stack.remove(word)
        pronunciation = result.pronunciation if result is not None else None
        context.memo[word] = pronunciation
        return pronunciation

    def segmentations(
        self,
        word: str,
        context: ResolveContext,
        *,
        max_components: int,
        max_states: int,
        limit: int = 16,
    ) -> tuple[tuple[str, ...], ...]:
        """Find spelling-only segmentations whose constituents resolve recursively."""
        cache: dict[tuple[int, int], tuple[tuple[str, ...], ...]] = {}

        def visit(position: int, count: int) -> tuple[tuple[str, ...], ...]:
            key = (position, count)
            if key in cache:
                return cache[key]
            context.states += 1
            if context.states > min(self.max_states, max_states):
                raise SearchLimitError(
                    f"recursive search limit {max_states} reached for {word!r}"
                )
            if position == len(word):
                result = ((),) if count >= 2 else ()
                cache[key] = result
                return result
            if count >= max_components:
                cache[key] = ()
                return ()
            candidates: list[tuple[str, ...]] = []
            for length in self._lengths.get(word[position], ()):
                end = position + length
                if end > len(word) or (end == len(word) and count == 0):
                    continue
                atom = word[position:end]
                if not self.membership.contains(atom):
                    continue
                if self.resolve(atom, context) is None:
                    continue
                for suffix in visit(end, count + 1):
                    candidates.append((atom, *suffix))
            result = tuple(
                sorted(set(candidates), key=segmentation_rank, reverse=True)[:limit]
            )
            cache[key] = result
            return result

        return visit(0, 0)
