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

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.reference.candidate import run_candidates
from benchmarks.reference.compare import compare_results
from benchmarks.reference.corpus import filter_cases, load_corpus
from benchmarks.reference.providers import ReferenceUnavailable
from benchmarks.reference.registry import (
    CANDIDATE_REGISTRY,
    REFERENCE_PROFILES,
    get_candidate_profile,
    get_reference_provider,
)
from benchmarks.reference.report import (
    compare_report_baseline,
    render_json,
    render_markdown,
)
from benchmarks.reference.types import (
    BenchmarkReport,
    CandidateProfile,
    Corpus,
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
) -> tuple[BenchmarkReport, tuple[ReferenceOutput, ...]]:
    candidate = candidate_profile or get_candidate_profile(candidate_id)
    corpus = filter_cases(
        load_corpus(corpus_name), case_ids=case_ids, tags=tags, limit=limit
    )
    provider = get_reference_provider(reference_id)
    candidate_outputs = run_candidates(corpus.cases, candidate)
    reference_outputs = tuple(
        provider.phonemize(
            case.text,
            case_id=case.id,
            language=candidate.language,
            model=candidate.target_model,
        )
        for case in corpus.cases
    )
    summary = compare_results(
        corpus.cases,
        candidate_outputs,
        reference_outputs,
        model=candidate.target_model,
        sample_limit=sample_limit,
    )
    report = BenchmarkReport(candidate, provider.metadata, corpus, summary)
    return report, reference_outputs


def _performance(corpus: Corpus, candidate_id: str) -> dict[str, object]:
    from benchmarks.reference.candidate import run_candidate

    profile = get_candidate_profile(candidate_id)
    start = time.perf_counter()
    for case in corpus.cases:
        run_candidate(case, profile)
    elapsed = time.perf_counter() - start
    rss_mb: float | None = None
    try:
        import resource

        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_mb = rss / (1024 * 1024) if sys.platform != "darwin" else rss / 1024
    except (ImportError, AttributeError):
        pass
    chars = sum(len(case.text) for case in corpus.cases)
    return {
        "process_cold_ms": None,
        "warm_total_ms": round(elapsed * 1000, 3),
        "sentences_per_second": len(corpus.cases) / elapsed if elapsed else None,
        "chars_per_second": chars / elapsed if elapsed else None,
        "process_peak_rss_mb": rss_mb,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "cpu_count": os.cpu_count(),
        "corpus_size": len(corpus.cases),
        "input_chars": chars,
        "input_utf8_bytes": sum(
            len(case.text.encode("utf-8")) for case in corpus.cases
        ),
    }


def _should_fail(report: BenchmarkReport, policy: str) -> bool:
    summary = report.summary
    if policy == "none":
        return False
    if policy == "candidate-error":
        return summary.candidate_success < summary.cases_total
    if policy in {"encoding-loss", "model-invalid"}:
        return bool(
            summary.candidate_encoding_loss or summary.candidate_encoding_failures
        )
    if policy == "regression":
        return bool(
            summary.candidate_encoding_loss or summary.candidate_encoding_failures
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
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--output", type=Path)
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


def main(argv: Sequence[str] | None = None, **defaults: str) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    reference_id = defaults.get("default_reference", args.reference)
    candidate_id = defaults.get("default_candidate", args.candidate)
    candidate_id = candidate_id or _default_candidate(reference_id)
    try:
        base_candidate = get_candidate_profile(candidate_id)
        candidate = replace(
            base_candidate,
            language=args.language or base_candidate.language,
            target_model=args.model or base_candidate.target_model,
        )
        corpus_name = args.corpus or _default_corpus(reference_id, candidate.language)
        report, reference_outputs = run_benchmark(
            reference_id=reference_id,
            candidate_id=candidate_id,
            corpus_name=corpus_name,
            case_ids=set(args.case_ids) if args.case_ids else None,
            tags=set(args.tags) if args.tags else None,
            limit=args.limit,
            sample_limit=args.sample_limit,
            candidate_profile=candidate,
        )
        if args.performance:
            report = BenchmarkReport(
                report.candidate,
                report.reference,
                report.corpus,
                report.summary,
                performance=_performance(report.corpus, candidate_id),
            )
    except (KeyError, FileNotFoundError, ValueError, ReferenceUnavailable) as exc:
        if args.strict_reference:
            parser.error(str(exc))
        print(f"reference unavailable: {exc}", file=sys.stderr)
        return 2

    if args.write_reference_golden:
        if args.write_reference_golden.exists() and not args.overwrite:
            parser.error(
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
        golden = json.loads(args.verify_reference_golden.read_text(encoding="utf-8"))
        current = _reference_golden_payload(report, reference_outputs)
        if golden.get("cases") != current.get("cases"):
            print("reference golden differs", file=sys.stderr)
            return 1

    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        print(json.dumps(compare_report_baseline(baseline, report.to_dict()), indent=2))

    output = render_markdown(report) if args.markdown else render_json(report)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    if args.only_differences or args.show_matches:
        selected = (
            report.summary.cases
            if args.show_matches
            else report.summary.difference_samples
        )
        for comparison in selected:
            print(f"{comparison.case_id}: {comparison.classification}")
            print(f"  candidate: {comparison.candidate.phonemes}")
            print(f"  reference: {comparison.reference.phonemes}")
    if _should_fail(report, args.fail_on):
        return 1
    if (
        args.strict_reference
        and report.summary.reference_success < report.summary.cases_total
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
