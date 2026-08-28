#!/usr/bin/env python3
"""Run the pinned Crane held-out word-to-IPA benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .crane_test_data import (
        CRANE_REPO,
        CRANE_REVISION,
        LANGUAGES,
        CraneBenchmarkError,
        benchmark_language,
        resolve_data_root,
        result_to_dict,
    )
except ImportError:
    from crane_test_data import (
        CRANE_REPO,
        CRANE_REVISION,
        LANGUAGES,
        CraneBenchmarkError,
        benchmark_language,
        resolve_data_root,
        result_to_dict,
    )

PROFILE_CONFIGS: dict[str, dict[str, Any]] = {
    "en_US": {
        "kokorog2p_language": "en-us",
        "use_espeak_fallback": True,
        "use_goruut_fallback": False,
        "use_spacy": False,
        "load_gold": True,
        "load_silver": True,
        "strict": True,
    },
    "de_DE": {
        "kokorog2p_language": "de-de",
        "use_espeak_fallback": True,
        "use_goruut_fallback": False,
        "use_spacy": False,
        "use_lexicon": True,
        "load_gold": True,
        "load_silver": True,
        "strip_stress": False,
    },
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark kokorog2p against the pinned Crane held-out G2P fixture."
    )
    parser.add_argument("--language", choices=["en_US", "de_DE", "all"], default="all")
    parser.add_argument(
        "--data-root", type=Path, help="Existing Crane checkout or extracted data root"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Explicitly download missing or changed assets at the pinned revision",
    )
    parser.add_argument(
        "--cache-dir", type=Path, help="Override the default benchmark cache directory"
    )
    parser.add_argument(
        "--limit", type=int, help="Run only the first N entries per language"
    )
    parser.add_argument("--output", type=Path, help="Write the complete result as JSON")
    parser.add_argument(
        "--worst", type=int, default=20, help="Number of worst mismatches to retain"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print worst mismatch examples"
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first conversion exception",
    )
    return parser.parse_args(argv)


def selected_languages(selection: str) -> list[str]:
    return list(LANGUAGES) if selection == "all" else [selection]


def print_summary(results: dict[str, dict[str, Any]]) -> None:
    print("Crane held-out G2P benchmark")
    print(f"Dataset: {CRANE_REPO}")
    print(f"Revision: {CRANE_REVISION}")
    print()
    print(
        f"{'Language':<10} {'Entries':>7} {'Exact match':>12} "
        f"{'CER':>10} {'Errors':>8} {'Speed':>12}"
    )
    print("-" * 65)
    for language, value in results.items():
        metrics = value["metrics"]
        print(
            f"{language:<10} {value['entries']:>7} "
            f"{metrics['exact_match_rate']:>11.2%} {metrics['cer']:>10.4f} "
            f"{metrics['exceptions']:>8} {metrics['words_per_second']:>10,.0f} w/s"
        )


def print_worst(results: dict[str, dict[str, Any]]) -> None:
    for language, value in results.items():
        cases = value["worst_cases"]
        if not cases:
            continue
        print(f"\nWorst mismatches for {language}:")
        for case in cases:
            print(
                f"  {case['word']!r}: expected={case['expected_kokoro']!r}, "
                f"actual={case['actual_kokoro']!r}, distance={case['edit_distance']}"
            )
            if case["error"]:
                print(f"    error: {case['error']}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.limit is not None and args.limit < 0:
        print("--limit must be non-negative", file=sys.stderr)
        return 2
    if args.worst < 0:
        print("--worst must be non-negative", file=sys.stderr)
        return 2

    languages = selected_languages(args.language)
    configs = [LANGUAGES[language] for language in languages]
    try:
        root = resolve_data_root(
            args.data_root,
            download=args.download,
            cache_dir=args.cache_dir,
            configs=configs,
        )
        serialized: dict[str, dict[str, Any]] = {}
        for language in languages:
            config = LANGUAGES[language]
            result = benchmark_language(
                config=config,
                data_root=root,
                limit=args.limit,
                worst_n=args.worst,
                fail_fast=args.fail_fast,
            )
            serialized[language] = result_to_dict(
                result,
                config=config,
                profile=PROFILE_CONFIGS[language],
            )
    except (CraneBenchmarkError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print_summary(serialized)
    if args.verbose:
        print_worst(serialized)
    if args.output:
        payload = {
            "benchmark": CRANE_REPO,
            "benchmark_schema": 1,
            "dataset_revision": CRANE_REVISION,
            "generated_at_utc": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "languages": serialized,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
