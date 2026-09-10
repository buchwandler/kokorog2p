"""JSON, Markdown, and concise terminal rendering for reference reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import BenchmarkReport, BenchmarkSuiteReport, ComparisonSummary


def render_json(
    report: BenchmarkReport | BenchmarkSuiteReport, *, indent: int = 2
) -> str:
    return (
        json.dumps(report.to_dict(), indent=indent, ensure_ascii=False, sort_keys=True)
        + "\n"
    )


def _duration(report: BenchmarkReport) -> str:
    total = report.execution.get("total_elapsed_ms")
    return f"{total:.0f} ms" if isinstance(total, (int, float)) else "n/a"


def _report_summary_line(report: BenchmarkReport) -> str:
    summary = report.summary
    return (
        f"[{report.verdict.upper()}] {report.candidate.id} vs {report.reference.provider_id} "
        f"[{report.reference_source}]\n"
        f"       {summary.cases_total} cases | gates {summary.policy_passed}/{summary.policy_cases} | "
        f"diagnostic differences {summary.diagnostic_differences}\n"
        f"       candidate errors {summary.candidate_errors} | model-invalid "
        f"{summary.candidate_encoding_failures + summary.candidate_encoding_loss} | "
        f"API-ID mismatch {summary.candidate_api_id_mismatches}\n"
        f"       exact agreement {summary.exact_phoneme_matches}/{summary.cases_total} | "
        f"{_duration(report)}"
    )


def _failure_cases(report: BenchmarkReport) -> list[Any]:
    return [
        case
        for case in report.summary.cases
        if case.policy_passed is False
        or not case.candidate_ok
        or not case.reference_ok
        or case.candidate_api_ids_consistent is False
        or case.classification
        in {"candidate-encoding-loss", "candidate-encoding-invalid"}
    ]


def render_summary(report: BenchmarkReport | BenchmarkSuiteReport) -> str:
    if isinstance(report, BenchmarkSuiteReport):
        lines = ["KokoroG2P reference compatibility [golden]", ""]
        lines.append(
            "RESULT  CANDIDATE       REFERENCE           CASES  GATES  FAIL  DIAG Δ  ERR  INVALID"
        )
        for item in report.reports:
            summary = item.summary
            lines.append(
                f"{item.verdict.upper():<7} {item.candidate.id:<15} {item.reference.provider_id:<19} "
                f"{summary.cases_total:>5}  {summary.policy_passed}/{summary.policy_cases:<4} "
                f"{summary.policy_failed:>4}  {summary.diagnostic_differences:>6}  "
                f"{summary.candidate_errors:>3}  "
                f"{summary.candidate_encoding_failures + summary.candidate_encoding_loss:>7}"
            )
        total_cases = sum(item.summary.cases_total for item in report.reports)
        total_passed = sum(item.summary.policy_passed for item in report.reports)
        total_gates = sum(item.summary.policy_cases for item in report.reports)
        total_diag = sum(item.summary.diagnostic_differences for item in report.reports)
        lines.extend(
            [
                "",
                f"[{report.verdict.upper()}] {total_cases} cases | "
                f"{total_passed}/{total_gates} gating expectations passed | "
                f"{total_diag} diagnostic differences",
            ]
        )
        return "\n".join(lines) + "\n"

    lines = [_report_summary_line(report)]
    failures = _failure_cases(report)
    if failures:
        lines.extend(["", "Failures:"])
        for case in failures:
            lines.append(f"  {case.case_id}  {case.policy:<10} {case.classification}")
            lines.append(f"      run with --case {case.case_id} --format markdown")
    return "\n".join(lines) + "\n"


def _summary_table(summary: ComparisonSummary) -> list[str]:
    lines = ["| Policy | Cases | Passed | Failed |", "|---|---:|---:|---:|"]
    for policy in ("exact", "normalized", "model-id", "model-valid", "diagnostic"):
        cases = summary.policy_counts.get(policy, 0)
        passed = sum(
            1
            for case in summary.cases
            if case.policy == policy and case.policy_passed is True
        )
        failed = sum(
            1
            for case in summary.cases
            if case.policy == policy and case.policy_passed is False
        )
        if cases:
            lines.append(f"| {policy} | {cases} | {passed} | {failed} |")
    return lines


def _context(left: str, right: str, index: int | None, radius: int = 12) -> str:
    if index is None:
        return ""
    start = max(0, index - radius)
    return f"candidate={left[start : index + radius]!r}; reference={right[start : index + radius]!r}"


def render_markdown(report: BenchmarkReport | BenchmarkSuiteReport) -> str:
    if isinstance(report, BenchmarkSuiteReport):
        lines = [
            "# KokoroG2P reference benchmark suite",
            "",
            f"**{report.verdict.upper()}**",
            "",
        ]
        for item in report.reports:
            lines.extend(render_markdown(item).splitlines())
            lines.append("\n---")
        return "\n".join(lines).rstrip() + "\n"

    summary = report.summary
    failures = _failure_cases(report)
    diagnostic = [
        case
        for case in summary.difference_samples
        if case not in failures and case.policy == "diagnostic"
    ]
    lines = [
        "# KokoroG2P reference benchmark",
        "",
        "## Verdict",
        "",
        f"**{report.verdict.upper()}**",
        f"Candidate: `{report.candidate.id}`",
        f"Reference: `{report.reference.provider_id}` @ `{report.reference.commit}`",
        f"Reference source: `{report.reference_source}`",
        f"Corpus: `{report.corpus.id}` (revision `{report.corpus.revision}`)",
        f"Cases: `{summary.cases_total}`",
        f"Duration: `{_duration(report)}`",
        "",
        "## Gating summary",
        "",
        *_summary_table(summary),
        "",
        "## Health invariants",
        "",
        "| Check | Result |",
        "|---|---:|",
        f"| Candidate errors | {summary.candidate_errors} |",
        f"| Candidate encoding failures | {summary.candidate_encoding_failures} |",
        f"| Candidate encoding loss | {summary.candidate_encoding_loss} |",
        f"| Candidate API-ID mismatches | {summary.candidate_api_id_mismatches} |",
        f"| Reference errors | {summary.reference_errors} |",
        "",
        "## Failures",
        "",
    ]
    if not failures:
        lines.append("No gating failures.")
    else:
        for case in failures:
            lines.extend(
                [
                    f"### `{case.case_id}` ({case.policy}, {case.classification})",
                    "",
                    f"Input: `{case.input_text}`",
                    f"Candidate: `{case.candidate.phonemes}`",
                    f"Reference: `{case.reference.phonemes}`",
                    f"Edit distance: `{case.symbol_diff.edit_distance}`",
                ]
            )
            if case.candidate.error:
                lines.append(f"Candidate error: `{case.candidate.error.message}`")
            if case.reference.error:
                lines.append(f"Reference error: `{case.reference.error.message}`")
            lines.append("")

    lines.extend(["## Diagnostic differences", ""])
    if not diagnostic:
        lines.append("No sampled diagnostic differences.")
    else:
        for case in diagnostic:
            lines.extend(
                [
                    f"### `{case.case_id}` ({case.classification})",
                    "",
                    f"Input: `{case.input_text}`",
                    f"Candidate: `{case.candidate.phonemes}`",
                    f"Reference: `{case.reference.phonemes}`",
                    f"Edit distance: `{case.symbol_diff.edit_distance}`",
                ]
            )
            context = _context(
                case.candidate.phonemes,
                case.reference.phonemes,
                case.symbol_diff.first_difference,
            )
            if context:
                lines.append(f"First-difference context: `{context}`")
            lines.append("")

    lines.extend(
        ["## Difference classes", "", "| Classification | Count |", "|---|---:|"]
    )
    for classification, count in sorted(summary.classification_counts.items()):
        lines.append(f"| {classification} | {count} |")
    lines.append("")
    if report.baseline is not None:
        lines.extend(
            [
                "## Baseline comparison",
                "",
                "```json",
                json.dumps(report.baseline, indent=2),
                "```",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def write_report(
    report: BenchmarkReport | BenchmarkSuiteReport,
    path: str | Path,
    *,
    markdown: bool = False,
) -> None:
    output = render_markdown(report) if markdown else render_json(report)
    Path(path).write_text(output, encoding="utf-8")


def _identity_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    identity = payload.get("identity")
    if isinstance(identity, dict):
        return identity
    return None


def compare_report_baseline(
    baseline: dict[str, Any], current: dict[str, Any]
) -> dict[str, Any]:
    """Compare metrics only after proving that report identities are compatible."""
    old_identity = _identity_from_payload(baseline)
    new_identity = _identity_from_payload(current)
    if old_identity is None or new_identity is None:
        return {"compatible": False, "error": "baseline lacks benchmark identity"}
    if old_identity != new_identity:
        return {
            "compatible": False,
            "error": "baseline identity differs",
            "baseline_identity": old_identity,
            "current_identity": new_identity,
        }
    old = baseline.get("summary", {})
    new = current.get("summary", {})
    return {
        "compatible": True,
        "exact_matches_decreased": new.get("exact_phoneme_matches", 0)
        < old.get("exact_phoneme_matches", 0),
        "model_id_matches_decreased": new.get("model_id_matches", 0)
        < old.get("model_id_matches", 0),
        "new_candidate_encoding_loss": new.get("candidate_encoding_loss", 0)
        > old.get("candidate_encoding_loss", 0),
        "new_candidate_errors": new.get("candidate_errors", 0)
        > old.get("candidate_errors", 0),
        "difference_count_increased": new.get("difference_count", 0)
        > old.get("difference_count", 0),
    }
