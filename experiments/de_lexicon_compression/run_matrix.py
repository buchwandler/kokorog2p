#!/usr/bin/env python3
"""Run source/mode compression and runtime measurements in subprocesses."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

try:
    from .lexlab.reports import write_json, write_tsv
except ImportError:  # direct script execution
    from lexlab.reports import write_json, write_tsv


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def run_matrix(
    sources: list[str], modes: list[str], *, data_root: Path | None, output: Path
) -> list[dict[str, object]]:
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for source in sources:
        for mode in modes:
            run_dir = output / f"{source}-{mode}"
            command = [
                sys.executable,
                str(Path(__file__).with_name("compress.py")),
                "--source",
                source,
                "--mode",
                mode,
                "--output",
                str(run_dir),
            ]
            if data_root:
                command.extend(("--data-root", str(data_root)))
            _run(command)
            runtime_path = run_dir / "runtime.json"
            runtime_command = [
                sys.executable,
                str(Path(__file__).with_name("benchmark_runtime.py")),
                "--run",
                str(run_dir),
                "--output",
                str(runtime_path),
            ]
            _run(runtime_command)
            summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "source": source,
                    "mode": mode,
                    "physical_rows": summary.get("physical_rows", 0),
                    "unique_words": summary.get("unique_words", 0),
                    "variants": summary.get("pronunciation_variants", 0),
                    "source_bytes": summary.get("source_bytes", 0),
                    "asset_bytes": summary.get("compressed_asset_bytes", 0),
                    "byte_reduction_pct": (1 - summary.get("compression_ratio", 0))
                    * 100,
                    "derived_words_pct": summary.get("entry_reduction_rate", 0) * 100,
                    "verification_failures": summary.get("verification", {}).get(
                        "failures", 0
                    ),
                    "compress_seconds": summary.get("performance", {}).get(
                        "compression_seconds", 0
                    ),
                    "verify_seconds": summary.get("performance", {}).get(
                        "verification_seconds", 0
                    ),
                    "peak_rss_mib": runtime.get("peak_rss_kib", 0) / 1024,
                    "cold_load_ms": runtime.get("cold_load_ms", 0),
                    "lookup_words_per_second": runtime.get("direct", {}).get(
                        "words_per_second", 0
                    ),
                }
            )
    fields = list(rows[0]) if rows else []
    write_tsv(output / "summary.tsv", rows, fields)
    write_json(output / "summary.json", {"schema": 1, "rows": rows})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True)
    parser.add_argument(
        "--modes", required=True, help="Comma-separated: exact-two-part,exact-multipart"
    )
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_matrix(
        [x.strip() for x in args.sources.split(",")],
        [x.strip() for x in args.modes.split(",")],
        data_root=args.data_root,
        output=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
