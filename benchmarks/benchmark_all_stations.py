#!/usr/bin/env python3
"""Run the station benchmark over every canonical kokorog2p target."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from benchmark_language_stations import LANGUAGES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fallback", choices=("on", "off"), default="on")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument(
        "--language",
        action="append",
        choices=sorted(LANGUAGES),
        help="Restrict to one or more languages. Repeat this option as needed.",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="Continue after an unavailable dependency or benchmark failure.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        help="Optional path for the aggregate factory matrix report.",
    )
    args = parser.parse_args()

    here = Path(__file__).resolve().parent
    selected = args.language or list(LANGUAGES)
    failures: list[tuple[str, int]] = []
    matrix: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="kokorog2p-factory-") as temp_dir:
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
                "--json",
                str(report_path),
            ]
            result = subprocess.run(command, check=False)
            if report_path.is_file():
                payload = json.loads(report_path.read_text(encoding="utf-8"))
                matrix[language] = payload.get("factory_summary", payload)
            elif result.returncode:
                matrix[language] = {
                    "status": "unavailable" if result.returncode == 2 else "failed",
                    "error": f"station benchmark exited {result.returncode}",
                }
            if result.returncode:
                failures.append((language, result.returncode))
                if not args.keep_going:
                    break
    print("\nFactory matrix:")
    print(
        "language factory_cold_ms factory_cached_ms first_phonemize_ms "
        "second_phonemize_ms optional_backend_created_during_factory "
        "rss_delta_factory_mib"
    )
    for language, summary in matrix.items():
        if summary.get("status") != "ok":
            print(f"{language:<8} {summary.get('status')}: {summary.get('error', '')}")
            continue
        print(
            f"{language:<8} {summary['factory_cold_ms']:>15.3f} "
            f"{summary['factory_cached_ms']:>17.3f} "
            f"{summary['first_phonemize_ms']:>18.3f} "
            f"{summary['second_phonemize_ms']:>19.3f} "
            f"{summary['optional_backend_created_during_factory']!s:>34} "
            f"{summary['rss_delta_factory_mib']!s:>21}"
        )
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(
                {"languages": matrix}, ensure_ascii=False, indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )

    if failures:
        print("\nFailures:")
        for language, code in failures:
            print(f"  {language}: exit {code}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
