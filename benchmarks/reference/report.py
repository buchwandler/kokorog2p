"""JSON and Markdown rendering for reference reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import BenchmarkReport, ComparisonSummary


def render_json(report: BenchmarkReport, *, indent: int = 2) -> str:
    return (
        json.dumps(report.to_dict(), indent=indent, ensure_ascii=False, sort_keys=True)
        + "\n"
    )


def _summary_lines(summary: ComparisonSummary) -> list[str]:
    cases_total = summary.cases_total
    return [
        f"Cases: {summary.cases_total}",
        f"Exact phoneme agreement: {summary.exact_phoneme_matches} / {cases_total}",
        f"Normalized agreement: {summary.normalized_phoneme_matches} / {cases_total}",
        f"Model-symbol agreement: {summary.model_symbol_matches} / {cases_total}",
        f"Model-ID agreement: {summary.model_id_matches} / {summary.cases_total}",
        f"Candidate errors: {summary.cases_total - summary.candidate_success}",
        f"Candidate encoding loss: {summary.candidate_encoding_loss}",
        f"Reference errors: {summary.cases_total - summary.reference_success}",
        f"Reference encoding loss: {summary.reference_encoding_loss}",
        f"Differences: {summary.difference_count}",
    ]


def render_markdown(report: BenchmarkReport) -> str:
    lines = [
        "# KokoroG2P reference benchmark",
        "",
        f"Candidate: `{report.candidate.id}`",
        f"Reference: `{report.reference.provider_id}` @ `{report.reference.commit}`",
        f"Frontend: `{report.reference.frontend}`",
        f"Corpus: `{report.corpus.id}` (revision `{report.corpus.revision}`)",
        "",
    ]
    lines.extend(_summary_lines(report.summary))
    lines.extend(["", "## Differences", ""])
    if not report.summary.difference_samples:
        lines.append("No differences.")
    for comparison in report.summary.difference_samples:
        first_difference = comparison.symbol_diff.first_difference
        lines.extend(
            [
                f"### `{comparison.case_id}` ({comparison.classification})",
                "",
                f"Input: {comparison.input_text}",
                "",
                f"Candidate: `{comparison.candidate.phonemes}`",
                f"Reference: `{comparison.reference.phonemes}`",
                f"First model-symbol difference: {first_difference}",
                f"Edit distance: {comparison.symbol_diff.edit_distance}",
                "",
            ]
        )
        if comparison.candidate.error:
            lines.append(f"Candidate error: `{comparison.candidate.error.message}`")
        if comparison.reference.error:
            lines.append(f"Reference error: `{comparison.reference.error.message}`")
    return "\n".join(lines).rstrip() + "\n"


def write_report(
    report: BenchmarkReport, path: str | Path, *, markdown: bool = False
) -> None:
    output = render_markdown(report) if markdown else render_json(report)
    Path(path).write_text(output, encoding="utf-8")


def compare_report_baseline(
    baseline: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Return stable metric regressions without interpreting reference upgrades."""
    old = baseline.get("summary", {})
    new = current.get("summary", {})
    return {
        "exact_matches_decreased": new.get("exact_phoneme_matches", 0)
        < old.get("exact_phoneme_matches", 0),
        "model_id_matches_decreased": new.get("model_id_matches", 0)
        < old.get("model_id_matches", 0),
        "new_candidate_encoding_loss": new.get("candidate_encoding_loss", 0)
        > old.get("candidate_encoding_loss", 0),
        "new_candidate_errors": new.get("candidate_success", 0)
        < old.get("candidate_success", 0),
        "difference_count_increased": new.get("difference_count", 0)
        > old.get("difference_count", 0),
    }
