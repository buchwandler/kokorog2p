"""Exact spelling/IPA composition with deterministic ranking."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from itertools import product

from .trie import PrefixTrie


class SearchLimitError(RuntimeError):
    """Composition search exceeded its defensive state limit."""


@dataclass(slots=True)
class CompositionMetrics:
    candidate_atom_prefixes_tested: int = 0
    dp_states_visited: int = 0
    cache_hits: int = 0
    search_states: int = 0
    max_search_states_per_word: int = 0

    @property
    def cache_hit_rate(self) -> float:
        total = self.dp_states_visited + self.cache_hits
        return self.cache_hits / total if total else 0.0


@dataclass(frozen=True, slots=True)
class Segmentation:
    components: tuple[str, ...]

    @property
    def lengths(self) -> tuple[int, ...]:
        return tuple(map(len, self.components))


def _ranking(
    segmentation: Segmentation,
) -> tuple[int, tuple[int, ...], tuple[str, ...]]:
    """Sort by fewer components, longest-leftmost lengths, then stable atom order."""
    return (
        -len(segmentation.components),
        segmentation.lengths,
        tuple(reversed(segmentation.components)),
    )


def choose_segmentation(
    word: str,
    atoms: Mapping[str, tuple[str, ...]],
    *,
    mode: str = "exact-multipart",
    max_states: int = 100_000,
    metrics: CompositionMetrics | None = None,
) -> Segmentation | None:
    """Choose a spelling-only segmentation; IPA is deliberately not inspected.

    The DP retains only the best suffix at each grapheme offset, so it does not
    materialize an exponential list of candidate segmentations.
    """
    if mode not in {"exact-two-part", "exact-multipart"}:
        raise ValueError(f"unknown composition mode: {mode}")
    trie = PrefixTrie(atoms)
    counter = [0]
    stats = metrics or CompositionMetrics()

    @cache
    def solve(position: int) -> tuple[str, ...] | None:
        if position == len(word):
            return ()
        stats.dp_states_visited += 1
        counter[0] += 1
        stats.search_states = counter[0]
        if counter[0] > max_states:
            raise SearchLimitError(f"search limit {max_states} reached for {word!r}")
        candidates: list[Segmentation] = []
        prefixes = trie.prefixes(word, position)
        stats.candidate_atom_prefixes_tested += len(prefixes)
        for atom in prefixes:
            tail = solve(position + len(atom))
            if tail is not None:
                candidates.append(Segmentation((atom, *tail)))
        best = max(candidates, key=_ranking, default=None)
        return best.components if best else None

    candidate = solve(0)
    stats.cache_hits += solve.cache_info().hits
    stats.max_search_states_per_word = max(stats.max_search_states_per_word, counter[0])
    if candidate is None or len(candidate) < 2:
        return None
    if mode == "exact-two-part" and len(candidate) != 2:
        return None
    return Segmentation(candidate)


def compose_variants(
    segmentation: Segmentation, atoms: Mapping[str, tuple[str, ...]]
) -> tuple[str, ...]:
    values = [atoms[component] for component in segmentation.components]
    return tuple("".join(parts) for parts in product(*values))


def exact_composition(
    word: str,
    expected: tuple[str, ...],
    atoms: Mapping[str, tuple[str, ...]],
    *,
    mode: str,
    max_states: int = 100_000,
    metrics: CompositionMetrics | None = None,
) -> tuple[Segmentation | None, tuple[str, ...]]:
    segmentation = choose_segmentation(
        word, atoms, mode=mode, max_states=max_states, metrics=metrics
    )
    if segmentation is None:
        return None, ()
    return segmentation, compose_variants(segmentation, atoms)
