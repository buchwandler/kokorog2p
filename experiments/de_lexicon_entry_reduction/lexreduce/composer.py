"""Bounded deterministic spelling-only composition."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .affixes import AffixTable
from .linkers import LinkerTable
from .prefix_index import LiteralPrefixIndex
from .rules import RuleSet


class SearchLimitError(RuntimeError):
    """The bounded composer exceeded its configured state budget."""


@dataclass(frozen=True, slots=True)
class DerivationResult:
    components: tuple[str, ...]
    pronunciation: tuple[str, ...]
    rule_id: str

    linker: str | None = None


def top_k_segmentations(
    word: str,
    prefix_index: LiteralPrefixIndex,
    literals: Mapping[str, tuple[str, ...]],
    *,
    k: int = 8,
    max_components: int = 4,
    max_states: int = 100_000,
) -> tuple[tuple[str, ...], ...]:
    """Enumerate a bounded, deterministic spelling-only segmentation frontier."""
    if k <= 0 or max_components < 2:
        return ()
    states = 0
    cache: dict[tuple[int, int], tuple[tuple[str, ...], ...]] = {}

    def visit(position: int, component_count: int) -> tuple[tuple[str, ...], ...]:
        nonlocal states
        key = (position, component_count)
        if key in cache:
            return cache[key]
        states += 1
        if states > max_states:
            raise SearchLimitError(f"search limit {max_states} reached for {word!r}")
        if position == len(word):
            result = ((),) if component_count >= 2 else ()
            cache[key] = result
            return result
        if component_count >= max_components:
            cache[key] = ()
            return ()
        candidates: list[tuple[str, ...]] = []
        for atom in prefix_index.prefixes(word, position, literals):
            for suffix in visit(position + len(atom), component_count + 1):
                candidates.append((atom, *suffix))
        result = tuple(sorted(set(candidates), key=segmentation_rank, reverse=True)[:k])
        cache[key] = result
        return result

    return visit(0, 0)


def segmentation_rank(
    components: tuple[str, ...],
) -> tuple[int, tuple[int, ...], tuple[str, ...]]:
    """Historical ranking: fewer components, longer-leftmost, lexical tie break."""

    return (-len(components), tuple(map(len, components)), tuple(reversed(components)))


def best_segmentation(
    word: str,
    prefix_index: LiteralPrefixIndex,
    literals: Mapping[str, tuple[str, ...]],
    *,
    max_components: int = 4,
    max_states: int = 100_000,
    scorer: Any | None = None,
) -> tuple[str, ...] | None:
    """Find one deterministic best decomposition without inspecting pronunciation."""

    if max_components < 2:
        return None
    states = 0
    cache: dict[tuple[int, int], tuple[str, ...] | None] = {}

    def visit(position: int, component_count: int) -> tuple[str, ...] | None:
        nonlocal states
        key = (position, component_count)
        if key in cache:
            return cache[key]
        states += 1
        if states > max_states:
            raise SearchLimitError(f"search limit {max_states} reached for {word!r}")
        if position == len(word):
            result = () if component_count >= 2 else None
            cache[key] = result
            return result
        if component_count >= max_components:
            cache[key] = None
            return None
        candidates: list[tuple[str, ...]] = []
        for atom in prefix_index.prefixes(word, position, literals):
            suffix = visit(position + len(atom), component_count + 1)
            if suffix is not None:
                candidates.append((atom, *suffix))
        result = (
            max(
                candidates,
                key=scorer.key if scorer is not None else segmentation_rank,
            )
            if candidates
            else None
        )
        cache[key] = result
        return result

    return visit(0, 0)


def best_two_part_segmentation(
    word: str,
    prefix_index: LiteralPrefixIndex,
    literals: Mapping[str, tuple[str, ...]],
) -> tuple[str, ...] | None:
    """Scan split points directly for the common two-component case."""

    candidates = [
        (word[:split], word[split:])
        for split in range(1, len(word))
        if word[:split] in literals and word[split:] in literals
    ]
    return max(candidates, key=segmentation_rank) if candidates else None


@dataclass(slots=True)
class ImplicitComposer:
    """Runtime composer whose derivation inputs contain no baseline oracle."""

    max_components: int = 4
    max_states: int = 100_000
    rules: RuleSet = None  # type: ignore[assignment]
    two_part_fast_path: bool = True

    linkers: LinkerTable | None = None
    recursive_components: bool = False
    max_recursive_depth: int = 4
    segmentation_scorer: Any | None = None
    affixes: AffixTable | None = None

    def __post_init__(self) -> None:
        if self.rules is None:
            self.rules = RuleSet()

    def derive(
        self,
        word: str,
        *,
        literals: Mapping[str, tuple[str, ...]],
        prefix_index: LiteralPrefixIndex,
        resolver: Any | None = None,
        context: Any | None = None,
    ) -> tuple[str, ...] | None:
        result = self.derive_result(
            word,
            literals=literals,
            prefix_index=prefix_index,
            resolver=resolver,
            context=context,
        )
        return result.pronunciation if result is not None else None

    def derive_result(
        self,
        word: str,
        *,
        literals: Mapping[str, tuple[str, ...]],
        prefix_index: LiteralPrefixIndex,
        resolver: Any | None = None,
        context: Any | None = None,
    ) -> DerivationResult | None:
        if self.two_part_fast_path and self.segmentation_scorer is None:
            components = best_two_part_segmentation(word, prefix_index, literals)
        else:
            components = None
        if components is None:
            components = best_segmentation(
                word,
                prefix_index,
                literals,
                max_components=self.max_components,
                max_states=self.max_states,
                scorer=self.segmentation_scorer,
            )
        if components is not None:
            rule_id, pronunciation = self.rules.derive_with_rule(
                word, components, literals
            )
            if rule_id is not None and pronunciation is not None:
                return DerivationResult(components, pronunciation, rule_id)
        if self.recursive_components and resolver is not None:
            if context is None:
                from .resolver import ResolveContext

                context = ResolveContext()
            recursive_segments = resolver.segmentations(
                word,
                context,
                max_components=self.max_components,
                max_states=self.max_states,
            )
            for recursive_components in recursive_segments:
                resolved_literals = dict(literals)
                complete = True
                for component in recursive_components:
                    pronunciation = resolver.resolve(component, context)
                    if pronunciation is None:
                        complete = False
                        break
                    resolved_literals[component] = pronunciation
                if not complete:
                    continue
                rule_id, pronunciation = self.rules.derive_with_rule(
                    word, recursive_components, resolved_literals
                )
                if rule_id is not None and pronunciation is not None:
                    return DerivationResult(
                        recursive_components, pronunciation, rule_id
                    )
        if self.affixes is not None:
            for affix_candidate in self.affixes.candidates(word, literals):
                temporary_literals = dict(literals)
                if affix_candidate.prefix:
                    temporary_literals[affix_candidate.prefix.spelling] = (
                        affix_candidate.prefix.pronunciation
                    )
                if affix_candidate.suffix:
                    temporary_literals[affix_candidate.suffix.spelling] = (
                        affix_candidate.suffix.pronunciation
                    )
                rule_id, pronunciation = self.rules.derive_with_rule(
                    word, affix_candidate.components, temporary_literals
                )
                if rule_id is not None and pronunciation is not None:
                    return DerivationResult(
                        affix_candidate.components, pronunciation, rule_id
                    )
        if self.linkers is None:
            return None
        for linker_candidate in self.linkers.candidates(word, literals):
            temporary_literals = dict(literals)
            temporary_literals[linker_candidate.linker.spelling] = (
                linker_candidate.linker.pronunciation
            )
            linker_components = linker_candidate.components
            rule_id, pronunciation = self.rules.derive_with_rule(
                word, linker_components, temporary_literals
            )
            if rule_id is not None and pronunciation is not None:
                return DerivationResult(
                    linker_components,
                    pronunciation,
                    rule_id,
                    linker_candidate.linker.spelling,
                )
        return None
