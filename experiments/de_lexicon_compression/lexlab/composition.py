"""Bounded exact spelling/IPA composition with deterministic ranking."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from itertools import product
from math import prod

from .trie import PrefixTrie


class SearchLimitError(RuntimeError):
    """Composition search exceeded its defensive state limit."""


@dataclass(slots=True)
class CompositionMetrics:
    candidate_atom_prefixes_tested: int = 0
    candidate_segmentations_tested: int = 0
    exact_segmentations_found: int = 0
    dp_states_visited: int = 0
    cache_hits: int = 0
    search_states: int = 0
    max_search_states_per_word: int = 0
    search_limit_words: int = 0
    best_exact_depth: int = 0
    max_variant_product: int = 0
    max_observed_variant_product: int = 0
    variant_product_rejections: int = 0
    trie_builds: int = 0
    trie_additions: int = 0

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
    """Prefer fewer components, then longer-leftmost, then stable atom order."""
    return (
        -len(segmentation.components),
        segmentation.lengths,
        tuple(reversed(segmentation.components)),
    )


def _index_for(
    atoms: Mapping[str, tuple[str, ...]], trie: PrefixTrie | None
) -> PrefixTrie:
    if trie is not None:
        return trie
    return PrefixTrie(atoms)


def _all_segmentations(
    word: str,
    atoms: Mapping[str, tuple[str, ...]],
    *,
    mode: str,
    trie: PrefixTrie | None,
    max_states: int,
    metrics: CompositionMetrics,
) -> tuple[Segmentation, ...]:
    """Enumerate spelling candidates, bounded by ``max_states`` DFS visits."""
    index = _index_for(atoms, trie)
    counter = 0
    candidates: list[Segmentation] = []

    def visit(position: int, components: tuple[str, ...]) -> None:
        nonlocal counter
        counter += 1
        metrics.search_states = counter
        if counter > max_states:
            raise SearchLimitError(f"search limit {max_states} reached for {word!r}")
        if position == len(word):
            if len(components) >= 2 and (
                mode == "exact-multipart" or len(components) == 2
            ):
                candidates.append(Segmentation(components))
            return
        if mode == "exact-two-part" and len(components) >= 2:
            return
        prefixes = index.prefixes(word, position)
        metrics.candidate_atom_prefixes_tested += len(prefixes)
        for atom in prefixes:
            visit(position + len(atom), (*components, atom))

    visit(0, ())
    metrics.max_search_states_per_word = max(
        metrics.max_search_states_per_word, counter
    )
    # The sort is stable because trie prefix order is deterministic.
    return tuple(sorted(candidates, key=_ranking, reverse=True))


def choose_segmentation(
    word: str,
    atoms: Mapping[str, tuple[str, ...]],
    *,
    mode: str = "exact-multipart",
    max_states: int = 100_000,
    metrics: CompositionMetrics | None = None,
    trie: PrefixTrie | None = None,
) -> Segmentation | None:
    """Choose the best spelling-only candidate.

    ``exact_composition`` intentionally searches all candidates instead of using
    this spelling-only winner.  The helper remains useful to callers that only
    need the historical deterministic spelling ranking.
    """
    if mode not in {"exact-two-part", "exact-multipart"}:
        raise ValueError(f"unknown composition mode: {mode}")
    stats = metrics or CompositionMetrics()
    candidates = _all_segmentations(
        word,
        atoms,
        mode=mode,
        trie=trie,
        max_states=max_states,
        metrics=stats,
    )
    return candidates[0] if candidates else None


def compose_variants(
    segmentation: Segmentation, atoms: Mapping[str, tuple[str, ...]]
) -> tuple[str, ...]:
    """Materialize a pronunciation product for small/direct callers."""
    values = [atoms[component] for component in segmentation.components]
    return tuple("".join(parts) for parts in product(*values))


def _lazy_matches(
    segmentation: Segmentation,
    expected: tuple[str, ...],
    atoms: Mapping[str, tuple[str, ...]],
) -> bool:
    values = [atoms[component] for component in segmentation.components]
    for expected_value, parts in zip(expected, product(*values), strict=True):
        if expected_value != "".join(parts):
            return False
    return True


def _candidate_product_size(
    segmentation: Segmentation, atoms: Mapping[str, tuple[str, ...]]
) -> int:
    return prod(len(atoms[component]) for component in segmentation.components)


def exact_composition(
    word: str,
    expected: tuple[str, ...],
    atoms: Mapping[str, tuple[str, ...]],
    *,
    mode: str,
    max_states: int = 100_000,
    max_variant_product: int = 100_000,
    metrics: CompositionMetrics | None = None,
    trie: PrefixTrie | None = None,
    candidate_observer: Callable[
        [tuple[Segmentation, ...], tuple[Segmentation, ...]], None
    ]
    | None = None,
) -> tuple[Segmentation | None, tuple[str, ...]]:
    """Return the highest-ranked candidate whose IPA tuple exactly matches.

    Spelling candidates are generated independently from IPA validation.  Variant
    products are cardinality-pruned and compared lazily, so a large mismatching
    Cartesian product is never materialized.
    """
    if mode not in {"exact-two-part", "exact-multipart"}:
        raise ValueError(f"unknown composition mode: {mode}")
    stats = metrics or CompositionMetrics()
    stats.max_variant_product = max(stats.max_variant_product, max_variant_product)
    candidates = _all_segmentations(
        word,
        atoms,
        mode=mode,
        trie=trie,
        max_states=max_states,
        metrics=stats,
    )
    first_candidate: tuple[str, ...] = ()
    exact: list[Segmentation] = []
    for segmentation in candidates:
        stats.candidate_segmentations_tested += 1
        product_size = _candidate_product_size(segmentation, atoms)
        stats.max_observed_variant_product = max(
            stats.max_observed_variant_product, product_size
        )
        if product_size != len(expected) or product_size > max_variant_product:
            stats.variant_product_rejections += 1
            continue
        if not first_candidate:
            first_candidate = compose_variants(segmentation, atoms)
        if _lazy_matches(segmentation, expected, atoms):
            exact.append(segmentation)
    if candidate_observer is not None:
        candidate_observer(candidates, tuple(exact))
    if exact:
        stats.exact_segmentations_found += len(exact)
        depth = len(exact[0].components)
        stats.best_exact_depth = (
            depth if not stats.best_exact_depth else min(stats.best_exact_depth, depth)
        )
        return exact[0], expected
    return None, first_candidate
