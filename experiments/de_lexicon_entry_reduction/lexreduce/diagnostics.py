"""Offline failure forensics for the V1 and V2 lexicon experiments.

This module intentionally accepts the canonical source and expected pronunciations.
It is an analysis tool and is never imported by the serialized runtime asset.
"""

from __future__ import annotations

import csv
import difflib
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon

from ..model import ImplicitLexicon
from .composer import SearchLimitError, top_k_segmentations


def _rule_candidates(
    asset: ImplicitLexicon,
    word: str,
    components: tuple[str, ...],
    literals: Mapping[str, tuple[str, ...]] | None = None,
) -> list[dict[str, Any]]:
    variants = tuple(
        (literals or asset.literals)[component] for component in components
    )
    candidates: list[dict[str, Any]] = []
    for rule in asset.composer.rules.rules:
        if rule.applies(word, components, variants):
            candidates.append(
                {
                    "rule_id": rule.rule_id,
                    "pronunciation": rule.compose(word, components, variants),
                }
            )
    return candidates


def _boundary_family(
    candidate: str,
    expected: str,
    components: tuple[str, ...] | None,
    variants: tuple[tuple[str, ...], ...] | None,
    window: int,
) -> dict[str, Any]:
    matcher = difflib.SequenceMatcher(a=candidate, b=expected, autojunk=False)
    opcodes = [opcode for opcode in matcher.get_opcodes() if opcode[0] != "equal"]
    boundaries: list[int] = []
    if components and variants:
        offset = 0
        for values in variants[:-1]:
            offset += len(values[0]) if values else 0
            boundaries.append(offset)
    local = (
        bool(opcodes)
        and all(
            any(abs(max(start, end) - boundary) <= window for boundary in boundaries)
            for _, start, end, _, _ in opcodes
        )
        if boundaries
        else False
    )
    template = (
        ";".join(
            f"{tag}:{candidate[i1:i2]!r}->{expected[j1:j2]!r}"
            for tag, i1, i2, j1, j2 in opcodes
        )
        or "equal"
    )
    if not local:
        family = "non-local mismatch"
    elif "ˈ" in candidate or "ˌ" in candidate or "ˈ" in expected or "ˌ" in expected:
        if "ˈ" in candidate and "ˌ" in expected:
            family = "primary stress → secondary stress"
        elif "ˈ" in expected and "ˈ" not in candidate:
            family = "insert stress"
        elif "ˈ" in candidate and "ˈ" not in expected:
            family = "delete stress"
        else:
            family = "other boundary-local replacement"
    elif len(candidate) != len(expected):
        family = "other boundary-local replacement"
    else:
        family = "local vowel/consonant alternation"
    return {"family": family, "template": template, "local": local, "opcodes": opcodes}


def analyze_failures(
    source: ParsedLexicon,
    asset: ImplicitLexicon,
    *,
    failures: Iterable[Mapping[str, Any]] = (),
    top_k: int = 16,
    boundary_window: int = 3,
) -> dict[str, Any]:
    """Classify retained words and compute offline oracle upper bounds."""
    failures_by_word = {str(item["word"]): item for item in failures}
    # BuildResult failures are normally supplied by the CLI. The fallback derives
    # the mutually exclusive classes from the reloaded asset and is still exact.
    classifications: dict[str, list[str]] = defaultdict(list)
    for word in asset.literals:
        item = failures_by_word.get(word)
        if item is None:
            classifications["forced-literal"].append(word)
        else:
            classifications[str(item.get("reason", "no-composition"))].append(word)
    for key in (
        "forced-literal",
        "search-limit",
        "no-composition",
        "pronunciation-mismatch",
    ):
        classifications.setdefault(key, [])

    alternate = Counter()
    topk_counts = Counter()
    family_counts: Counter[str] = Counter()
    family_patterns: dict[tuple[str, str], dict[str, Any]] = {}
    mismatch_details: list[dict[str, Any]] = []
    segmentation_by_depth: Counter[str] = Counter()
    selected_by_rule: Counter[str] = Counter()
    source_words = set(source.words)

    # A report may include builder failure data as a private analysis attachment;
    # it is never serialized in an asset. Recompute missing failure records here.
    for word in classifications["pronunciation-mismatch"]:
        expected = source.lookup_all(word)
        item = failures_by_word.get(word, {})
        components_value = item.get("candidate_components")
        components = tuple(components_value) if components_value else None
        candidate_value = item.get("candidate")
        candidate = tuple(candidate_value) if candidate_value else ()
        if components:
            candidates = _rule_candidates(asset, word, components)
            selected_rule = str(item.get("candidate_rule") or "unknown")
            selected_by_rule[selected_rule] += 1
            exact_rules = [
                str(row["rule_id"])
                for row in candidates
                if tuple(row["pronunciation"]) == expected
            ]
            alternate["selected_rule_exact"] += int(selected_rule in exact_rules)
            alternate["alternate_existing_rule_exact"] += int(
                bool(exact_rules) and selected_rule not in exact_rules
            )
            alternate["multiple_existing_rules_exact"] += int(len(exact_rules) > 1)
            alternate["no_existing_rule_exact"] += int(not exact_rules)
        try:
            segmentations = top_k_segmentations(
                word,
                asset.literal_index,
                asset.literals,
                k=top_k,
                max_components=asset.composer.max_components,
                max_states=asset.composer.max_states,
            )
        except SearchLimitError:
            segmentations = ()
        exact_rank: int | None = None
        for rank, segmentation in enumerate(segmentations, 1):
            if any(
                tuple(row["pronunciation"]) == expected
                for row in _rule_candidates(asset, word, segmentation)
            ):
                exact_rank = rank
                break
        if exact_rank == 1:
            topk_counts["exact_on_rank_1"] += 1
        elif exact_rank is not None:
            topk_counts["exact_on_rank_2_to_k"] += 1
        else:
            topk_counts["not_exact_in_top_k"] += 1
        if components:
            segmentation_by_depth[str(len(components))] += 1
        selected_rule = str(item.get("candidate_rule") or "unknown")
        selected_by_rule[selected_rule] += 0
        actual = candidate[0] if candidate else ""
        expected_first = expected[0] if expected else ""
        variants = (
            tuple(asset.literals[component] for component in components)
            if components
            else None
        )
        boundary = _boundary_family(
            actual, expected_first, components, variants, boundary_window
        )
        family_counts[boundary["family"]] += 1
        key = (boundary["family"], boundary["template"])
        pattern = family_patterns.setdefault(
            key,
            {
                "support_count": 0,
                "exact_count_if_applied": 0,
                "conflict_count": 0,
                "word_count": 0,
                "component_count": len(components or ()),
                "spelling_left_context": components[0][-3:] if components else "",
                "spelling_right_context": components[-1][:3] if components else "",
                "phoneme_left_context": actual[-3:],
                "phoneme_right_context": expected_first[:3],
                "edit_template": boundary["template"],
            },
        )
        pattern["support_count"] += 1
        pattern["word_count"] += 1
        mismatch_details.append(
            {
                "word": word,
                "selected_segmentation": list(components or ()),
                "component_count": len(components or ()),
                "component_spellings": list(components or ()),
                "selected_rule": selected_rule,
                "candidate_pronunciation": list(candidate),
                "expected_pronunciation": list(expected),
                "stress_signature": [
                    {
                        "count": sum(value.count("ˈ") for value in values),
                        "values": list(values),
                    }
                    for values in (variants or ())
                ],
                "boundary": boundary,
                "word_length": len(word),
                "component_lengths": [len(component) for component in components or ()],
                "top_k_exact_rank": exact_rank,
            }
        )

    oracle_provenance = (
        "offline-only; expected IPA is used for analysis and " + "never runtime lookup"
    )
    linker_summary = linker_diagnostics(source, asset)
    result: dict[str, Any] = {
        "oracle_provenance": oracle_provenance,
        "baseline_word_count": len(source_words),
        "retained_groups": {
            key: len(value) for key, value in sorted(classifications.items())
        },
        "retained_words": {
            key: sorted(value) for key, value in sorted(classifications.items())
        },
        "pronunciation_mismatch_count": len(classifications["pronunciation-mismatch"]),
        "alternate_rule_summary": dict(alternate),
        "linker_summary": linker_summary,
        "top_k_segmentation_summary": {
            "k": top_k,
            **dict(topk_counts),
            "by_component_depth": dict(segmentation_by_depth),
            "by_selected_rule": dict(selected_by_rule),
        },
        "failure_family_summary": {
            "boundary_window": boundary_window,
            "baseline_word_count": len(source_words),
            "retained_groups": {
                key: len(value) for key, value in sorted(classifications.items())
            },
            "pronunciation_mismatch_count": len(
                classifications["pronunciation-mismatch"]
            ),
            "counts": dict(family_counts),
            "boundary_local_recoverable_count": sum(
                count
                for family, count in family_counts.items()
                if family != "non-local mismatch"
            ),
        },
        "failure_details": mismatch_details,
        "boundary_patterns": sorted(
            family_patterns.values(),
            key=lambda value: (
                -int(value["support_count"]),
                str(value["edit_template"]),
            ),
        ),
    }
    return result


def linker_diagnostics(source: ParsedLexicon, asset: ImplicitLexicon) -> dict[str, Any]:
    """Measure linker candidate opportunities offline against expected IPA."""
    table = asset.composer.linkers
    if table is None:
        return {
            "words_newly_segmentable_due_to_linkers": 0,
            "words_newly_exact_due_to_linkers": 0,
            "per_linker": {},
        }
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    newly_segmentable = 0
    newly_exact = 0
    for word in source.words:
        if word in asset.literals:
            continue
        candidates = table.candidates(word, asset.literals)
        if not candidates:
            continue
        newly_segmentable += 1
        expected = source.lookup_all(word)
        exact = False
        for candidate in candidates:
            temporary = dict(asset.literals)
            temporary[candidate.linker.spelling] = candidate.linker.pronunciation
            rules = _rule_candidates(asset, word, candidate.components, temporary)
            if any(tuple(row["pronunciation"]) == expected for row in rules):
                exact = True
                counts[candidate.linker.spelling]["exact_count"] += 1
                break
            counts[candidate.linker.spelling]["mismatch_count"] += 1
        if exact:
            newly_exact += 1
    return {
        "words_newly_segmentable_due_to_linkers": newly_segmentable,
        "words_newly_exact_due_to_linkers": newly_exact,
        "per_linker": {key: dict(value) for key, value in sorted(counts.items())},
        "linker_rule_bytes": len(json.dumps(table.as_dict(), sort_keys=True).encode()),
    }


def write_diagnostics(directory: Path, result: Mapping[str, Any]) -> None:
    """Write the stable JSON and TSV diagnostic artifacts."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "failure_family_summary.json").write_text(
        json.dumps(result["failure_family_summary"], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    (directory / "alternate_rule_summary.json").write_text(
        json.dumps(result["alternate_rule_summary"], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    (directory / "linker_summary.json").write_text(
        json.dumps(result["linker_summary"], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (directory / "top_k_segmentation_summary.json").write_text(
        json.dumps(result["top_k_segmentation_summary"], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    patterns = result["boundary_patterns"][:100]
    fields = (
        "support_count",
        "exact_count_if_applied",
        "conflict_count",
        "word_count",
        "component_count",
        "spelling_left_context",
        "spelling_right_context",
        "phoneme_left_context",
        "phoneme_right_context",
        "edit_template",
    )
    with (directory / "top_100_boundary_patterns.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(
            {field: pattern.get(field, "") for field in fields} for pattern in patterns
        )
    detail_fields = (
        "word",
        "selected_rule",
        "selected_segmentation",
        "candidate_pronunciation",
        "expected_pronunciation",
        "top_k_exact_rank",
    )
    with (directory / "failure_families.tsv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=detail_fields, delimiter="\t")
        writer.writeheader()
        for detail in result["failure_details"]:
            writer.writerow({field: detail.get(field, "") for field in detail_fields})
