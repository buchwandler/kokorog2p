"""Metrics and human-readable reports for candidate runs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .builder import BuildResult
from .serializer import runtime_asset_bytes


def summary_dict(
    result: BuildResult,
    *,
    verification: dict[str, Any] | None = None,
    asset_directory: Path | None = None,
) -> dict[str, Any]:
    asset = result.asset
    metrics = result.metrics
    membership = asset.membership
    index = asset.literal_index
    rules = asset.composer.rules
    failure_counts = Counter(
        str(item.get("reason", "unknown")) for item in result.failures
    )
    linker_bytes = (
        len(json.dumps(asset.composer.linkers.as_dict(), sort_keys=True).encode())
        if asset.composer.linkers
        else 0
    )
    affix_bytes = (
        len(json.dumps(asset.composer.affixes.as_dict(), sort_keys=True).encode())
        if asset.composer.affixes
        else 0
    )
    summary: dict[str, Any] = {
        "baseline_word_count": metrics.baseline_word_count,
        "target_literal_word_count": int(
            asset.metadata.get("target_literal_word_count", 400_000)
        ),
        "literal_word_count": metrics.literal_word_count,
        "generated_word_count": metrics.generated_word_count,
        "per_generated_word_recipe_count": metrics.per_generated_word_recipe_count,
        "entry_reduction_count": metrics.entry_reduction_count,
        "entry_reduction_rate": metrics.entry_reduction_rate,
        "target_met": metrics.literal_word_count
        <= int(asset.metadata.get("target_literal_word_count", 400_000)),
        "lossless": bool(verification and verification.get("lossless", False)),
        "verification": verification or {},
        "source_sha256": asset.source.sha256,
        "literal_reduction_rate": metrics.entry_reduction_rate,
        "failure_decomposition": {
            "no_composition_count": failure_counts["no-composition"],
            "pronunciation_mismatch_count": failure_counts["pronunciation-mismatch"],
            "search_limit_count": failure_counts["search-limit"],
        },
        "representation": {
            "membership_states": membership.state_count,
            "membership_edges": membership.edge_count,
            "membership_bytes": membership.serialized_bytes,
            "literal_index_states": index.state_count,
            "literal_index_edges": index.edge_count,
            "rule_count": len(rules.rules),
            "rule_bytes": len(json.dumps(rules.as_dict(), sort_keys=True).encode()),
            "selector_bytes": (
                len(json.dumps(rules.selector.as_dict(), sort_keys=True).encode())
                if rules.selector
                else 0
            ),
            "linker_affix_bytes": linker_bytes + affix_bytes,
            "linker_bytes": linker_bytes,
            "affix_bytes": affix_bytes,
            "runtime_asset_bytes": runtime_asset_bytes(asset_directory)
            if asset_directory
            else None,
        },
        "search_limit_words": result.search_limit_words,
        "rule_usage": rules.as_dict()["rules"],
    }
    return summary


def report_markdown(
    summary: dict[str, Any], *, runtime: dict[str, Any] | None = None
) -> str:
    verification = summary.get("verification", {})
    memory = runtime or {}
    yes_no = lambda value: "yes" if value else "no"
    baseline_rss = memory.get("baseline_rss_delta_bytes", "not measured")
    candidate_rss = memory.get("candidate_rss_delta_bytes", "not measured")
    additional_literal_removal = summary.get("additional_literal_removal_vs_v1", 0)
    return f"""# German resident lexicon reduction result

Baseline literal words: {summary["baseline_word_count"]:,}
Candidate literal words: {summary["literal_word_count"]:,}
Implicitly generated baseline words: {summary["generated_word_count"]:,}
Literal-entry reduction: {summary["entry_reduction_rate"]:.2%}
Target: <= {summary["target_literal_word_count"]:,}
Target met: {yes_no(summary["target_met"])}
Per-generated-word runtime recipes: {summary["per_generated_word_recipe_count"]}

Source SHA-256: {summary.get("source_sha256", "unknown")}
Additional generated words versus V1: {summary.get("additional_generated_vs_v1", 0):,}
Additional literal removal versus V1: {additional_literal_removal:,}
Configuration: {summary.get("configuration", {})}

Lossless verification:
- words checked: {verification.get("words_checked", 0):,}
- missing: {verification.get("missing_words", 0):,}
- extra membership hits: {verification.get("extra_words", 0):,}
- pronunciation mismatches: {verification.get("pronunciation_mismatches", 0):,}
- variant-order mismatches: {verification.get("variant_order_mismatches", 0):,}
- lossless: {yes_no(summary["lossless"])}

Memory:
- baseline fresh-process RSS delta: {baseline_rss}
- candidate fresh-process RSS delta: {candidate_rss}
- RSS saved: {memory.get("rss_saved_bytes", "not measured")}
"""


def write_reports(directory: Path, summary: dict[str, Any]) -> None:
    (directory / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    (directory / "report.md").write_text(report_markdown(summary), encoding="utf-8")
