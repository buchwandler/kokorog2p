#!/usr/bin/env python3
"""Run model-aware KokoroG2P compatibility benchmarks."""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.reference.candidate import run_candidates
from benchmarks.reference.compare import compare_results
from benchmarks.reference.corpus import filter_cases, load_corpus
from benchmarks.reference.golden import load_reference_golden, select_reference_outputs
from benchmarks.reference.providers import ReferenceUnavailable
from benchmarks.reference.registry import (
    CANDIDATE_REGISTRY,
    REFERENCE_PROFILES,
    get_candidate_profile,
    get_reference_provider,
    get_reference_suite,
)
from benchmarks.reference.report import (
    compare_report_baseline,
    render_json,
    render_markdown,
    render_summary,
)
from benchmarks.reference.types import (
    BenchmarkReport,
    BenchmarkSuiteReport,
    CandidateProfile,
    ReferenceOutput,
)


def _default_candidate(reference_id: str) -> str:
    if "de-" in reference_id:
        return "de-default"
    return "en-gb-default" if "gb" in reference_id else "en-us-default"


def _default_corpus(reference_id: str, candidate_language: str) -> str:
    if candidate_language == "de" or "de-" in reference_id:
        return "de"
    return "en-gb" if "gb" in reference_id else "en-us"


def _reference_golden_payload(
    report: BenchmarkReport, outputs: Sequence[ReferenceOutput]
) -> dict[str, object]:
    return {
        "schema_version": report.schema_version,
        "reference": report.reference.to_dict(),
        "corpus": report.corpus.to_dict(),
        "cases": [output.to_dict() for output in outputs],
    }


def _verdict(summary: Any) -> str:
    if (
        summary.reference_errors
        or summary.reference_encoding_failures
        or summary.reference_encoding_loss
    ):
        return "error"
    if (
        summary.candidate_errors
        or summary.candidate_encoding_failures
        or summary.candidate_encoding_loss
        or summary.candidate_api_id_mismatches
        or summary.policy_failed
    ):
        return "fail"
    return "pass"


def run_benchmark(
    *,
    reference_id: str,
    candidate_id: str,
    corpus_name: str,
    case_ids: set[str] | None = None,
    tags: set[str] | None = None,
    limit: int | None = None,
    sample_limit: int = 100,
    candidate_profile: CandidateProfile | None = None,
    reference_source: str = "live",
) -> tuple[BenchmarkReport, tuple[ReferenceOutput, ...]]:
    """Execute one candidate/reference comparison exactly once."""
    if reference_source not in {"golden", "live"}:
        raise ValueError(f"unsupported reference source: {reference_source}")
    candidate = candidate_profile or get_candidate_profile(candidate_id)
    provider: Any = None
    golden = None
    if reference_source == "golden":
        golden = load_reference_golden(reference_id)
        corpus = golden.corpus
        reference_metadata = golden.metadata
    else:
        corpus = load_corpus(corpus_name)
        provider = get_reference_provider(reference_id)
        provider.prepare()
        reference_metadata = provider.metadata

    corpus = filter_cases(corpus, case_ids=case_ids, tags=tags, limit=limit)
    candidate_start = time.perf_counter()
    candidate_outputs = run_candidates(corpus.cases, candidate)
    candidate_elapsed_ms = (time.perf_counter() - candidate_start) * 1000

    reference_start = time.perf_counter()
    if golden is not None:
        selected_ids = {case.id for case in corpus.cases}
        reference_outputs = select_reference_outputs(golden, selected_ids)
        if len(reference_outputs) != len(corpus.cases):
            raise ValueError("golden selection does not match selected corpus cases")
    else:
        reference_outputs = tuple(
            provider.phonemize(
                case.text,
                case_id=case.id,
                language=candidate.language,
                model=candidate.target_model,
            )
            for case in corpus.cases
        )
    reference_elapsed_ms = (time.perf_counter() - reference_start) * 1000
    summary = compare_results(
        corpus.cases,
        candidate_outputs,
        reference_outputs,
        model=candidate.target_model,
        sample_limit=sample_limit,
    )
    report = BenchmarkReport(
        candidate=candidate,
        reference=reference_metadata,
        corpus=corpus,
        summary=summary,
        verdict=_verdict(summary),
        reference_source=reference_source,
        execution={
            "candidate_elapsed_ms": round(candidate_elapsed_ms, 3),
            "reference_elapsed_ms": round(reference_elapsed_ms, 3),
            "total_elapsed_ms": round(candidate_elapsed_ms + reference_elapsed_ms, 3),
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    )
    return report, reference_outputs


def _rss_mb() -> float | None:
    try:
        import resource
    except (ImportError, AttributeError):
        return None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / (1024 * 1024) if sys.platform == "darwin" else rss / 1024


def _performance(report: BenchmarkReport) -> dict[str, object]:
    """Return descriptive execution metadata without rerunning compatibility cases."""
    result = dict(report.execution)
    result["process_peak_rss_mb"] = _rss_mb()
    seconds = report.execution.get("total_elapsed_ms", 0) / 1000
    result["sentences_per_second"] = (
        report.summary.cases_total / seconds if seconds else None
    )
    chars = sum(len(case.text) for case in report.corpus.cases)
    result.update(
        {
            "chars_per_second": chars / seconds if seconds else None,
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "corpus_size": len(report.corpus.cases),
            "input_chars": chars,
            "input_utf8_bytes": sum(
                len(case.text.encode("utf-8")) for case in report.corpus.cases
            ),
        }
    )
    return result


def _should_fail(report: BenchmarkReport, policy: str) -> bool:
    summary = report.summary
    if policy == "none":
        return False
    if policy == "candidate-error":
        return summary.candidate_errors > 0
    if policy in {"encoding-loss", "model-invalid"}:
        return bool(
            summary.candidate_encoding_loss or summary.candidate_encoding_failures
        )
    if policy == "regression":
        return bool(
            summary.candidate_errors
            or summary.candidate_encoding_failures
            or summary.candidate_encoding_loss
            or summary.candidate_api_id_mismatches
            or summary.policy_failed
        )
    if policy == "any-difference":
        return summary.difference_count > 0
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="KokoroG2P reference compatibility benchmark"
    )
    parser.add_argument(
        "--reference", choices=sorted(REFERENCE_PROFILES), default="hexgrad-en-us-v1"
    )
    parser.add_argument("--candidate", choices=sorted(CANDIDATE_REGISTRY))
    parser.add_argument("--language")
    parser.add_argument("--model")
    parser.add_argument("--corpus", default=None)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--tag", action="append", dest="tags")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--sample-limit", type=int, default=100)
    parser.add_argument("--only-differences", action="store_true")
    parser.add_argument("--show-matches", action="store_true")
    parser.add_argument(
        "--format", choices=("summary", "json", "markdown"), default=None
    )
    parser.add_argument("--json", action="store_const", const="json", dest="format")
    parser.add_argument(
        "--markdown", action="store_const", const="markdown", dest="format"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument(
        "--reference-source", choices=("golden", "live"), default="live"
    )
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--suite", choices=("core",))
    parser.add_argument("--strict-reference", action="store_true")
    parser.add_argument(
        "--fail-on",
        choices=[
            "none",
            "candidate-error",
            "encoding-loss",
            "model-invalid",
            "regression",
            "any-difference",
        ],
        default="none",
    )
    parser.add_argument("--performance", action="store_true")
    parser.add_argument("--write-reference-golden", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--verify-reference-golden", type=Path)
    parser.add_argument("--baseline", type=Path)
    return parser


def _selected_report(
    report: BenchmarkReport, args: argparse.Namespace
) -> BenchmarkReport:
    if not args.only_differences and not args.show_matches:
        return report
    selected = (
        tuple(item for item in report.summary.cases if not item.exact_phoneme_match)
        if args.only_differences
        else report.summary.cases
    )
    summary = replace(
        report.summary,
        cases=selected,
        difference_samples=tuple(
            item for item in selected if not item.exact_phoneme_match
        ),
    )
    return replace(report, summary=summary)


def _suite_verdict(reports: Sequence[BenchmarkReport]) -> str:
    if any(report.verdict == "error" for report in reports):
        return "error"
    if any(report.verdict == "fail" for report in reports):
        return "fail"
    return "pass"


def _render(report: BenchmarkReport | BenchmarkSuiteReport, output_format: str) -> str:
    if output_format == "summary":
        return render_summary(report)
    if output_format == "markdown":
        return render_markdown(report)
    return render_json(report)


def _exit_code(report: BenchmarkReport | BenchmarkSuiteReport, fail_on: str) -> int:
    if report.verdict == "error":
        return 2
    if report.verdict == "fail" or (
        isinstance(report, BenchmarkReport) and _should_fail(report, fail_on)
    ):
        return 1
    return 0


def _run_one(
    args: argparse.Namespace,
    reference_id: str,
    candidate_id: str,
    corpus_override: str | None = None,
) -> BenchmarkReport:
    base_candidate = get_candidate_profile(candidate_id)
    candidate = replace(
        base_candidate,
        language=args.language or base_candidate.language,
        target_model=args.model or base_candidate.target_model,
    )
    corpus_name = (
        corpus_override
        or args.corpus
        or _default_corpus(reference_id, candidate.language)
    )
    report, reference_outputs = run_benchmark(
        reference_id=reference_id,
        candidate_id=candidate_id,
        corpus_name=corpus_name,
        case_ids=set(args.case_ids) if args.case_ids else None,
        tags=set(args.tags) if args.tags else None,
        limit=args.limit,
        sample_limit=args.sample_limit,
        candidate_profile=candidate,
        reference_source=args.reference_source,
    )
    if args.performance:
        report = replace(report, performance=_performance(report))
    if args.write_reference_golden:
        if args.write_reference_golden.exists() and not args.overwrite:
            raise ValueError(
                f"golden exists; pass --overwrite: {args.write_reference_golden}"
            )
        args.write_reference_golden.write_text(
            json.dumps(
                _reference_golden_payload(report, reference_outputs),
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
    if args.verify_reference_golden:
        golden = load_reference_golden(reference_id, args.verify_reference_golden)
        if tuple(output.to_dict() for output in golden.outputs) != tuple(
            output.to_dict() for output in reference_outputs
        ):
            raise ValueError("reference golden differs")
    return report


def main(argv: Sequence[str] | None = None, **defaults: str) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.quick:
        args.reference_source = "golden"
        args.format = "summary"
        args.fail_on = "regression"
        args.sample_limit = min(args.sample_limit, 5)
    reference_id = defaults.get("default_reference", args.reference)
    candidate_id = defaults.get(
        "default_candidate", args.candidate
    ) or _default_candidate(reference_id)
    try:
        if args.suite:
            suite = get_reference_suite(args.suite)
            reports = tuple(
                _run_one(args, suite_reference, suite_candidate, suite_corpus)
                for suite_reference, suite_candidate, suite_corpus in suite
            )
            report: BenchmarkReport | BenchmarkSuiteReport = BenchmarkSuiteReport(
                suite=args.suite,
                reports=reports,
                verdict=_suite_verdict(reports),
            )
        else:
            report = _run_one(args, reference_id, candidate_id)
            if args.baseline:
                baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
                comparison = compare_report_baseline(baseline, report.to_dict())
                report = replace(report, baseline=comparison)
                if not comparison.get("compatible", False):
                    report = replace(report, verdict="error")
            report = _selected_report(report, args)
    except (
        KeyError,
        FileNotFoundError,
        ValueError,
        ReferenceUnavailable,
        json.JSONDecodeError,
    ) as exc:
        print(f"reference benchmark error: {exc}", file=sys.stderr)
        return 2

    output_format = args.format or "json"
    rendered = _render(report, output_format)
    if args.json_output:
        args.json_output.write_text(_render(report, "json"), encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.write_text(_render(report, "markdown"), encoding="utf-8")
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return _exit_code(report, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())
