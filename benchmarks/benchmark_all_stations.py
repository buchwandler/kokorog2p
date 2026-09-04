#!/usr/bin/env python3
"""Run the station benchmark over every canonical kokorog2p target."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from .benchmark_language_stations import LANGUAGES
except ImportError:
    from benchmark_language_stations import LANGUAGES


def _failure_text(language: str, payload: dict[str, Any]) -> str:
    status = payload.get("status", "failed")
    phase = payload.get("phase", "unknown")
    sentence = payload.get("sentence_index")
    location = phase
    if sentence is not None:
        location += f" sentence={sentence}"
    error = payload.get("error", {})
    if isinstance(error, dict):
        error_text = f"{error.get('type', 'Error')}: {error.get('message', '')}"
    else:
        error_text = str(error)
    return f"{language:<8} {status:<12} {location:<28} {error_text}".rstrip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run station benchmarks for all supported languages."
    )
    parser.add_argument("--fallback", choices=("on", "off"), default="on")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--language", action="append", choices=sorted(LANGUAGES))
    parser.add_argument("--corpus", choices=("smoke", "scaled"), default="smoke")
    parser.add_argument("--target-chars", type=int, default=2000)
    parser.add_argument(
        "--call-shape", choices=("sentences", "paragraph", "both"), default="sentences"
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue after an unavailable dependency or benchmark failure.",
    )
    parser.add_argument(
        "--json", type=Path, help="Optional path for the aggregate report."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.runs < 1:
        raise SystemExit("--runs must be at least one")
    selected = args.language or list(LANGUAGES)
    here = Path(__file__).resolve().parent
    reports: dict[str, dict[str, Any]] = {}
    factory_matrix: dict[str, dict[str, Any]] = {}
    failures: list[tuple[str, int, dict[str, Any]]] = []

    with tempfile.TemporaryDirectory(prefix="kokorog2p-stations-") as temp_dir:
        for index, language in enumerate(selected, start=1):
            if index > 1:
                print("\n" + "=" * 80 + "\n", flush=True)
            print(f"[{index}/{len(selected)}] {language}", flush=True)
            report_path = Path(temp_dir) / f"{language.replace('-', '_')}.json"
            command = [
                sys.executable,
                str(here / "benchmark_language_stations.py"),
                "--language",
                language,
                "--fallback",
                args.fallback,
                "--runs",
                str(args.runs),
                "--corpus",
                args.corpus,
                "--target-chars",
                str(args.target_chars),
                "--call-shape",
                args.call_shape,
                "--json",
                str(report_path),
            ]
            result = subprocess.run(
                command, check=False, capture_output=True, text=True
            )
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="", file=sys.stderr)

            if report_path.is_file():
                try:
                    payload = json.loads(report_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    payload = {
                        "schema_version": 2,
                        "status": "failed",
                        "language": language,
                        "phase": "aggregate/read-report",
                        "error": {"type": type(exc).__name__, "message": str(exc)},
                        "stdout_tail": result.stdout[-1000:],
                        "stderr": result.stderr[-1000:],
                    }
            else:
                payload = {
                    "schema_version": 2,
                    "status": "failed" if result.returncode != 2 else "unavailable",
                    "language": language,
                    "phase": "child/startup",
                    "error": {
                        "type": "ChildProcessError",
                        "message": (
                            f"station benchmark exited {result.returncode} "
                            "before writing a report"
                        ),
                    },
                    "probe_exit_code": result.returncode,
                    "stderr": result.stderr,
                    "stdout_tail": result.stdout[-1000:],
                }
            reports[language] = payload
            factory_matrix[language] = payload.get("factory_summary", payload)
            status = payload.get("status")
            if (
                result.returncode
                or status != "ok"
                or payload.get("output_equal") is False
            ):
                failures.append(
                    (
                        language,
                        result.returncode or (2 if status == "unavailable" else 1),
                        payload,
                    )
                )
                if not args.keep_going:
                    break

    print("\nFactory matrix:")
    print(
        "language status       process_cold_ms factory_construct_ms "
        "factory_cache_hit_ms direct_first_ms direct_warm_ms "
        "prepared_first_ms prepared_warm_ms"
    )
    for language, summary in factory_matrix.items():
        if summary.get("status") != "ok":
            print(_failure_text(language, summary))
            continue
        print(
            f"{language:<8} {summary.get('status', 'ok'):<12} "
            f"{summary.get('process_cold_ms', 0):>15.3f} "
            f"{summary.get('factory_construct_ms', 0):>20.3f} "
            f"{summary.get('factory_cache_hit_ms', 0):>20.3f} "
            f"{summary.get('direct_first_ms', 0):>15.3f} "
            f"{summary.get('direct_warm_ms', 0):>14.3f} "
            f"{summary.get('prepared_first_ms', 0):>17.3f} "
            f"{summary.get('prepared_warm_ms', 0):>16.3f}"
        )

    if failures:
        print("\nFailures:")
        for language, _code, payload in failures:
            print("  " + _failure_text(language, payload))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {
                    "schema_version": 2,
                    "languages": reports,
                    "factory_matrix": factory_matrix,
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
