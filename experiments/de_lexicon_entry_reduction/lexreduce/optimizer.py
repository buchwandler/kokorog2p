"""Offline utility-aware literal-basis promotion heuristic."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon

from .affixes import AffixTable
from .builder import BuildResult, build_implicit_lexicon
from .composer import ImplicitComposer
from .linkers import LinkerTable
from .rules import RuleSet


@dataclass(frozen=True, slots=True)
class OptimizationPass:
    pass_number: int
    promoted_word: str
    before_literal_count: int
    after_literal_count: int
    words_removed_due_to_promotion: int
    net_literal_reduction: int


@dataclass(slots=True)
class OptimizationResult:
    build: BuildResult
    passes: list[OptimizationPass]
    reached_target: bool


def _promotion_candidates(
    source: ParsedLexicon,
    result: BuildResult,
    *,
    limit: int = 64,
) -> tuple[str, ...]:
    """Rank generated baseline substrings using an offline occurrence index."""
    literal_words = set(result.asset.literals)
    baseline_words = set(source.words)
    scores: Counter[str] = Counter()
    for failure in result.failures:
        word = str(failure["word"])
        if failure.get("reason") not in ("pronunciation-mismatch", "no-composition"):
            continue
        for start in range(len(word)):
            for end in range(start + 1, len(word) + 1):
                candidate = word[start:end]
                if candidate in baseline_words and candidate not in literal_words:
                    scores[candidate] += 1
    return tuple(sorted(scores, key=lambda word: (-scores[word], word))[:limit])


def optimize_basis(
    source: ParsedLexicon,
    *,
    composer: ImplicitComposer | None = None,
    rules: RuleSet | None = None,
    linkers: LinkerTable | None = None,
    affixes: AffixTable | None = None,
    recursive_components: bool = False,
    max_recursive_depth: int = 4,
    max_components: int = 4,
    max_states: int = 100_000,
    segmentation_scorer: object | None = None,
    max_passes: int = 4,
    target_literals: int = 400_000,
    candidate_limit: int = 64,
) -> OptimizationResult:
    """Promote atoms only when a complete exact rebuild lowers literals."""
    promoted: set[str] = set()
    current = build_implicit_lexicon(
        source,
        composer=composer,
        rules=rules,
        linkers=linkers,
        affixes=affixes,
        recursive_components=recursive_components,
        max_recursive_depth=max_recursive_depth,
        max_components=max_components,
        max_states=max_states,
        segmentation_scorer=segmentation_scorer,
        forced_literals=promoted,
    )
    passes: list[OptimizationPass] = []
    candidates_evaluated = 0
    full_rebuilds = 1
    for pass_number in range(1, max_passes + 1):
        if current.metrics.literal_word_count <= target_literals:
            break
        before = current.metrics.literal_word_count
        selected: tuple[str, BuildResult, int] | None = None
        for candidate in _promotion_candidates(source, current, limit=candidate_limit):
            candidates_evaluated += 1
            if candidate in promoted:
                continue
            trial_promoted = promoted | {candidate}
            trial = build_implicit_lexicon(
                source,
                composer=None,
                rules=rules,
                linkers=linkers,
                affixes=affixes,
                recursive_components=recursive_components,
                max_recursive_depth=max_recursive_depth,
                max_components=max_components,
                max_states=max_states,
                segmentation_scorer=segmentation_scorer,
                forced_literals=trial_promoted,
            )
            full_rebuilds += 1
            reduction = before - trial.metrics.literal_word_count
            if reduction > (selected[2] if selected else 0):
                selected = (candidate, trial, reduction)
        if selected is None:
            break
        candidate, current, reduction = selected
        promoted.add(candidate)
        passes.append(
            OptimizationPass(
                pass_number,
                candidate,
                before,
                current.metrics.literal_word_count,
                max(0, before + 1 - current.metrics.literal_word_count),
                reduction,
            )
        )
    current.asset.metadata.update(
        {
            "optimizer": "utility",
            "optimization_pass_count": len(passes),
            "promoted_word_count": len(passes),
            "words_removed_due_to_promotions": sum(
                item.words_removed_due_to_promotion for item in passes
            ),
            "net_literal_reduction": sum(item.net_literal_reduction for item in passes),
            "optimizer_candidates_evaluated": candidates_evaluated,
            "optimizer_full_rebuilds": full_rebuilds,
        }
    )
    return OptimizationResult(
        current,
        passes,
        current.metrics.literal_word_count <= target_literals,
    )
