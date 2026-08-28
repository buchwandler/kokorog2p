"""Offline construction of an implicit literal basis."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon

from ..model import CandidateMetrics, ImplicitLexicon, LiteralLexicon
from .affixes import AffixTable
from .composer import ImplicitComposer, SearchLimitError
from .linkers import LinkerTable
from .membership import MembershipIndex
from .prefix_index import MutableLiteralPrefixIndex
from .resolver import ComponentResolver, ResolveContext
from .rules import RuleSet


@dataclass(slots=True)
class BuildResult:
    asset: ImplicitLexicon
    metrics: CandidateMetrics
    failures: list[dict[str, Any]] = field(default_factory=list)
    membership_enumeration_matches: bool = True
    search_limit_words: int = 0


def build_implicit_lexicon(
    source: ParsedLexicon,
    *,
    composer: ImplicitComposer | None = None,
    rules: RuleSet | None = None,
    max_components: int = 4,
    max_states: int = 100_000,
    forced_literals: Iterable[str] = (),
    linkers: LinkerTable | None = None,
    recursive_components: bool = False,
    max_recursive_depth: int = 4,
    segmentation_scorer: Any | None = None,
    affixes: AffixTable | None = None,
) -> BuildResult:
    """Build a candidate, using source IPA only for the offline keep decision."""

    if composer is None:
        composer = ImplicitComposer(
            max_components=max_components,
            max_states=max_states,
            rules=rules,
            linkers=linkers,
            recursive_components=recursive_components,
            max_recursive_depth=max_recursive_depth,
            segmentation_scorer=segmentation_scorer,
            affixes=affixes,
        )
    elif rules is not None:
        composer.rules = rules
    if linkers is not None:
        composer.linkers = linkers
    if recursive_components:
        composer.recursive_components = True
        composer.max_recursive_depth = max_recursive_depth
    if segmentation_scorer is not None:
        composer.segmentation_scorer = segmentation_scorer
    if affixes is not None:
        composer.affixes = affixes
    forced = set(forced_literals)
    literals: dict[str, tuple[str, ...]] = {}
    prefix_index = MutableLiteralPrefixIndex.empty()
    failures: list[dict[str, Any]] = []
    generated_count = 0
    search_limit_words = 0

    membership = MembershipIndex.from_words(source.words)
    resolver = (
        ComponentResolver(
            membership,
            composer,
            literals,
            prefix_index,
            max_depth=max_recursive_depth,
            max_states=max_states,
        )
        if recursive_components
        else None
    )
    ordered_words = sorted(source.words, key=lambda word: (len(word), word))
    for word in ordered_words:
        expected = source.lookup_all(word)
        result = None
        if word not in forced:
            try:
                result = composer.derive_result(
                    word,
                    literals=literals,
                    prefix_index=prefix_index,
                    resolver=resolver,
                    context=ResolveContext() if resolver is not None else None,
                )
            except SearchLimitError as exc:
                search_limit_words += 1
                failures.append(
                    {
                        "word": word,
                        "reason": "search-limit",
                        "error": str(exc),
                        "candidate": None,
                    }
                )
        if result is not None and result.pronunciation == expected:
            generated_count += 1
            composer.rules.record_result(result.rule_id, True)
            continue

        if result is not None:
            composer.rules.record_result(result.rule_id, False)
        literals[word] = expected
        prefix_index.add(word)
        if word not in forced:
            failures.append(
                {
                    "word": word,
                    "reason": "pronunciation-mismatch" if result else "no-composition",
                    "candidate": result.pronunciation if result else None,
                    "candidate_components": result.components if result else None,
                    "candidate_rule": result.rule_id if result else None,
                    "candidate_depth": len(result.components) if result else None,
                }
            )

    enumeration_matches = membership.iter_words() == tuple(sorted(source.words))
    metadata: dict[str, object] = {
        "schema": 1,
        "kind": "implicit-entry-reduction",
        "baseline_word_count": len(source.entries),
        "generated_word_count": generated_count,
        "per_generated_word_recipe_count": 0,
        "target_literal_word_count": 400_000,
        "composer_version": composer.rules.composer_version,
        "membership_version": 1,
        "rule_version": "1",
        "search_limit_words": search_limit_words,
        "membership_enumeration_matches": enumeration_matches,
    }
    asset = ImplicitLexicon(
        source=source.source,
        literals=LiteralLexicon(literals),
        literal_index=prefix_index.freeze(),
        membership=membership,
        composer=composer,
        metadata=metadata,
    )
    return BuildResult(
        asset,
        CandidateMetrics(len(source.entries), len(literals), generated_count),
        failures,
        enumeration_matches,
        search_limit_words,
    )
