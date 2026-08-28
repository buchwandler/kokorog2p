#!/usr/bin/env python3
"""Run offline V1 failure forensics; expected IPA never enters runtime assets."""

from __future__ import annotations

import argparse
import ast
import csv
from pathlib import Path

try:
    from .lexreduce.diagnostics import analyze_failures, write_diagnostics
    from .lexreduce.serializer import load_asset
    from .source import load_canonical_source
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.de_lexicon_entry_reduction.lexreduce.diagnostics import (
        analyze_failures,
        write_diagnostics,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.serializer import load_asset
    from experiments.de_lexicon_entry_reduction.source import load_canonical_source


def _parse_value(value: str) -> object:
    if not value:
        return None
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def read_failures(path: Path) -> list[dict[str, object]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = []
        for row in csv.DictReader(handle, delimiter="\t"):
            rows.append({key: _parse_value(value) for key, value in row.items()})
        return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="builtin")
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--top-k-segmentations", type=int, default=16)
    parser.add_argument("--boundary-window", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--path", type=Path)
    args = parser.parse_args()

    source = load_canonical_source(
        args.source, data_root=args.data_root, path=args.path
    )
    asset = load_asset(args.run / "candidate.asset")
    failure_path = args.run / "literal_failures.tsv"
    failures = read_failures(failure_path) if failure_path.is_file() else []
    result = analyze_failures(
        source,
        asset,
        failures=failures,
        top_k=args.top_k_segmentations,
        boundary_window=args.boundary_window,
    )
    write_diagnostics(args.output, result)
    print(
        f"analysed {result['baseline_word_count']} words; "
        f"{result['pronunciation_mismatch_count']} pronunciation mismatches"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
