"""Build exact atom/exception compositions from one source at a time."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from time import perf_counter

from .composition import CompositionMetrics, SearchLimitError, exact_composition
from .decoder import CompressedLexicon
from .model import ParsedLexicon
from .trie import PrefixTrie


@dataclass(slots=True)
class CompressionResult:
    compressed: CompressedLexicon
    metrics: CompositionMetrics
    failures: list[dict[str, object]] = field(default_factory=list)
    component_usage: list[dict[str, object]] = field(default_factory=list)
    derivation_depth: list[dict[str, object]] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    failure_counts: dict[str, int] = field(default_factory=dict)
    ambiguity: list[dict[str, object]] = field(default_factory=list)

    @property
    def derived_words(self) -> int:
        return len(self.compressed.derived)


def compress_lexicon(
    source: ParsedLexicon,
    *,
    mode: str = "exact-multipart",
    max_states: int = 100_000,
    max_variant_product: int = 100_000,
    failure_sample_limit: int = 100,
    full_failures: bool = False,
) -> CompressionResult:
    if mode not in {
        "baseline",
        "baseline-canonical",
        "exact-two-part",
        "exact-multipart",
    }:
        raise ValueError(f"unknown compression mode: {mode}")
    effective_mode = "baseline" if mode == "baseline-canonical" else mode
    started = perf_counter()
    direct: dict[str, tuple[str, ...]] = {}
    derived: dict[str, tuple[str, ...]] = {}
    metrics = CompositionMetrics(max_variant_product=max_variant_product)
    failures: list[dict[str, object]] = []
    failure_counts: Counter[str] = Counter()
    ambiguities: list[dict[str, object]] = []
    depths: list[dict[str, object]] = []

    def record_failure(
        word: str, reason: str, candidate: tuple[str, ...], components: str
    ) -> None:
        failure_counts[reason] += 1
        if full_failures or len(failures) >= failure_sample_limit:
            return
        expected = source.lookup_all(word)
        failures.append(
            {
                "source": source.source.source_id,
                "word": word,
                "variant_index": "",
                "expected": "|".join(expected),
                "candidate": "|".join(candidate),
                "components": components,
                "reason": reason,
            }
        )

    def observe_candidates(candidates, exact_candidates) -> None:
        if len(candidates) > 1 or len(exact_candidates) > 1:
            ambiguities.append(
                {
                    "word": current_word,
                    "spelling_candidate_count": len(candidates),
                    "exact_candidate_count": len(exact_candidates),
                    "selected_components": "|".join(
                        exact_candidates[0].components if exact_candidates else ()
                    ),
                    "alternative_exact_components": ";".join(
                        "|".join(candidate.components)
                        for candidate in exact_candidates[1:]
                    ),
                    "selection_reason": (
                        "best-ranked-exact"
                        if exact_candidates
                        else "no-exact-candidate"
                    ),
                }
            )

    if effective_mode == "baseline":
        direct = {word: source.lookup_all(word) for word in sorted(source.words)}
        compressed = CompressedLexicon(
            source.source,
            {},
            direct,
            {},
            {
                "mode": mode,
                "compressor_version": "2",
                "lossless_contract": "lookup-semantic",
            },
        )
        return CompressionResult(
            compressed=compressed,
            metrics=metrics,
            elapsed_seconds=perf_counter() - started,
        )

    # This index is deliberately created once and populated only when an entry
    # must remain direct.  Rebuilding it inside choose_segmentation is quadratic.
    trie = PrefixTrie()
    metrics.trie_builds = 1
    for word in sorted(source.words, key=lambda value: (len(value), value)):
        expected = source.lookup_all(word)
        current_word = word
        try:
            segmentation, candidate = exact_composition(
                word,
                expected,
                direct,
                mode=effective_mode,
                max_states=max_states,
                max_variant_product=max_variant_product,
                metrics=metrics,
                trie=trie,
                candidate_observer=observe_candidates,
            )
        except SearchLimitError:
            metrics.search_limit_words += 1
            segmentation, candidate = None, ()
            record_failure(word, "SEARCH_LIMIT", candidate, "")
        if segmentation is not None and candidate == expected:
            derived[word] = segmentation.components
            component_count = len(segmentation.components)
            depths.append(
                {
                    "word": word,
                    "components": "|".join(segmentation.components),
                    "depth": component_count,
                }
            )
        else:
            direct[word] = expected
            trie.add(word)
            metrics.trie_additions += 1
            if segmentation is None:
                reason = "NO_ORTHOGRAPHIC_SEGMENTATION"
            elif not candidate:
                reason = "VARIANT_PRODUCT_REJECTED"
            else:
                reason = "VARIANT_TUPLE_MISMATCH"
            record_failure(
                word,
                reason,
                candidate,
                "|".join(segmentation.components) if segmentation else "",
            )

    used = {component for components in derived.values() for component in components}
    atoms = {word: direct.pop(word) for word in sorted(used)}
    exceptions = {word: direct[word] for word in sorted(direct)}

    # These counters are updated from the accepted derivations rather than by
    # scanning every atom against every derived word after the pass.
    component_word_uses: Counter[str] = Counter()
    component_occurrences: Counter[str] = Counter()
    component_variant_uses: Counter[str] = Counter()
    for word, components in derived.items():
        component_word_uses.update(set(components))
        component_occurrences.update(components)
        component_variant_uses.update(
            {component: len(source.lookup_all(word)) for component in set(components)}
        )

    usage = []
    for atom, values in atoms.items():
        usage.append(
            {
                "atom": atom,
                "pronunciation_variant_count": len(values),
                "derived_word_uses": component_word_uses[atom],
                "component_occurrences": component_occurrences[atom],
                "derived_variant_uses": component_variant_uses[atom],
                "estimated_rows_saved": component_variant_uses[atom],
                "estimated_bytes_saved": 0,
            }
        )
    compressed = CompressedLexicon(
        source.source,
        atoms,
        exceptions,
        derived,
        {
            "mode": mode,
            "compressor_version": "2",
            "lossless_contract": "lookup-semantic",
            "failure_reporting": "full" if full_failures else "sampled",
            "failure_sample_limit": failure_sample_limit,
        },
    )
    return CompressionResult(
        compressed=compressed,
        metrics=metrics,
        failures=failures,
        component_usage=usage,
        derivation_depth=depths,
        elapsed_seconds=perf_counter() - started,
        failure_counts=dict(sorted(failure_counts.items())),
        ambiguity=ambiguities,
    )
