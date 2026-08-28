#!/usr/bin/env python3
"""Build and verify one implicit entry-reduction candidate."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from .lexreduce.affixes import german_affix_table
    from .lexreduce.builder import build_implicit_lexicon
    from .lexreduce.linkers import german_linker_table
    from .lexreduce.optimizer import optimize_basis
    from .lexreduce.reports import report_markdown, summary_dict
    from .lexreduce.rules import default_rules
    from .lexreduce.segmentation import SegmentationScorer
    from .lexreduce.selector import extract_features, train_selector
    from .lexreduce.serializer import load_asset, save_asset
    from .source import load_canonical_source
    from .verify import verify_candidate
except ImportError:  # direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.de_lexicon_entry_reduction.lexreduce.affixes import (
        german_affix_table,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.builder import (
        build_implicit_lexicon,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.linkers import (
        german_linker_table,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.optimizer import (
        optimize_basis,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.reports import (
        report_markdown,
        summary_dict,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.rules import default_rules
    from experiments.de_lexicon_entry_reduction.lexreduce.segmentation import (
        SegmentationScorer,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.selector import (
        extract_features,
        train_selector,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.serializer import (
        load_asset,
        save_asset,
    )
    from experiments.de_lexicon_entry_reduction.source import load_canonical_source
    from experiments.de_lexicon_entry_reduction.verify import verify_candidate


def _train_v2_selector(source, base_build, rules):
    rows = []
    for failure in base_build.failures:
        components_value = failure.get("candidate_components")
        if not components_value:
            continue
        components = tuple(components_value)
        if any(component not in base_build.asset.literals for component in components):
            continue
        variants = tuple(
            base_build.asset.literals[component] for component in components
        )
        expected = source.lookup_all(str(failure["word"]))
        exact = [
            rule.rule_id
            for rule in rules.rules
            if rule.applies(str(failure["word"]), components, variants)
            and rule.compose(str(failure["word"]), components, variants) == expected
        ]
        target_rule = (
            "C0" if "C0" in exact else str(failure.get("candidate_rule") or "C1")
        )
        rows.append(
            {
                "features": extract_features(
                    str(failure["word"]), components, variants
                ),
                "target_rule": target_rule,
            }
        )
    return train_selector(
        rows,
        default_rule="C1"
        if any(rule.rule_id == "C1" for rule in rules.rules)
        else "C0",
        min_support=100,
        max_leaves=64,
    )


def run(
    source_id: str,
    mode: str,
    output: Path,
    *,
    data_root: Path | None = None,
    path: Path | None = None,
    target_literals: int = 400_000,
    max_components: int = 4,
    max_states: int = 100_000,
    optimizer: str = "greedy",
    max_passes: int = 4,
    selector: str = "v1",
    boundary_rules: str = "v1",
    linkers: str = "v1",
    recursive_components: bool = False,
    max_recursive_depth: int = 4,
    segmentation_scorer: str = "v1",
    affixes: str = "v1",
) -> dict[str, object]:
    source = load_canonical_source(source_id, data_root=data_root, path=path)
    compound = mode == "implicit-compound"
    if boundary_rules not in ("v1", "v2"):
        raise ValueError(f"unknown boundary rules: {boundary_rules}")
    if linkers not in ("v1", "german"):
        raise ValueError(f"unknown linkers: {linkers}")
    if segmentation_scorer not in ("v1", "v2"):
        raise ValueError(f"unknown segmentation scorer: {segmentation_scorer}")
    if affixes not in ("v1", "german"):
        raise ValueError(f"unknown affixes: {affixes}")
    use_boundary_rules = boundary_rules == "v2"
    linker_table = german_linker_table() if linkers == "german" else None
    scorer = SegmentationScorer() if segmentation_scorer == "v2" else None
    affix_table = german_affix_table() if affixes == "german" else None
    rules = default_rules(compound, boundary_rules=use_boundary_rules)
    if selector == "v2":
        base_build = build_implicit_lexicon(
            source,
            rules=rules,
            max_components=max_components,
            max_states=max_states,
            linkers=linker_table,
            recursive_components=recursive_components,
            max_recursive_depth=max_recursive_depth,
            segmentation_scorer=scorer,
            affixes=affix_table,
        )
        selector_model = _train_v2_selector(source, base_build, rules)
        rules = default_rules(
            compound, selector=selector_model, boundary_rules=use_boundary_rules
        )
    elif selector != "v1":
        raise ValueError(f"unknown selector: {selector}")
    if optimizer == "utility":
        optimized = optimize_basis(
            source,
            rules=rules,
            linkers=linker_table,
            recursive_components=recursive_components,
            max_recursive_depth=max_recursive_depth,
            max_components=max_components,
            max_states=max_states,
            segmentation_scorer=scorer,
            affixes=affix_table,
            max_passes=max_passes,
            target_literals=target_literals,
        )
        build = optimized.build
    else:
        build = build_implicit_lexicon(
            source,
            rules=rules,
            max_components=max_components,
            max_states=max_states,
            linkers=linker_table,
            recursive_components=recursive_components,
            max_recursive_depth=max_recursive_depth,
            segmentation_scorer=scorer,
            affixes=affix_table,
        )
    build.asset.metadata["target_literal_word_count"] = target_literals
    output.mkdir(parents=True, exist_ok=True)
    asset_directory = output / "candidate.asset"
    save_asset(asset_directory, build.asset)
    reloaded = load_asset(asset_directory)
    verification = verify_candidate(reloaded, source)
    summary = summary_dict(
        build, verification=verification, asset_directory=asset_directory
    )
    summary["mode"] = mode
    summary["optimizer"] = optimizer
    summary["configuration"] = {
        "selector": selector,
        "boundary_rules": boundary_rules,
        "linkers": linkers,
        "recursive_components": recursive_components,
        "max_recursive_depth": max_recursive_depth,
        "segmentation_scorer": segmentation_scorer,
        "affixes": affixes,
        "optimizer": optimizer,
    }
    (output / "verification.json").write_text(
        json.dumps(verification, indent=2) + "\n", encoding="utf-8"
    )
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (output / "report.md").write_text(report_markdown(summary), encoding="utf-8")
    _write_failures(output / "literal_failures.tsv", build.failures)
    (output / "rules.json").write_text(
        json.dumps(build.asset.composer.rules.as_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return summary


def _write_failures(path: Path, failures: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "word",
                "reason",
                "candidate",
                "candidate_components",
                "candidate_rule",
            ),
            delimiter="\t",
        )
        writer.writeheader()
        for failure in failures:
            writer.writerow({key: failure.get(key, "") for key in writer.fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="builtin")
    parser.add_argument(
        "--mode", choices=("implicit-concat", "implicit-compound"), required=True
    )
    parser.add_argument("--target-literals", type=int, default=400_000)
    parser.add_argument("--max-components", type=int, default=4)
    parser.add_argument("--max-states", type=int, default=100_000)
    parser.add_argument("--optimizer", choices=("greedy", "utility"), default="greedy")
    parser.add_argument("--selector", choices=("v1", "v2"), default="v1")
    parser.add_argument("--boundary-rules", choices=("v1", "v2"), default="v1")
    parser.add_argument("--linkers", choices=("v1", "german"), default="v1")
    parser.add_argument("--recursive-components", action="store_true")
    parser.add_argument("--max-recursive-depth", type=int, default=4)
    parser.add_argument("--segmentation-scorer", choices=("v1", "v2"), default="v1")
    parser.add_argument("--affixes", choices=("v1", "german"), default="v1")
    parser.add_argument("--max-passes", type=int, default=4)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--path", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(
        args.source,
        args.mode,
        args.output,
        data_root=args.data_root,
        path=args.path,
        target_literals=args.target_literals,
        max_components=args.max_components,
        max_states=args.max_states,
        optimizer=args.optimizer,
        max_passes=args.max_passes,
        selector=args.selector,
        boundary_rules=args.boundary_rules,
        linkers=args.linkers,
        recursive_components=args.recursive_components,
        max_recursive_depth=args.max_recursive_depth,
        segmentation_scorer=args.segmentation_scorer,
        affixes=args.affixes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
