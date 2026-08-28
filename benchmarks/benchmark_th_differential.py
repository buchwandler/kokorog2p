#!/usr/bin/env python3
"""Development-only differential benchmark for the clean-room Thai frontend.

The reference checkout is an operator-provided oracle. It is never imported by
kokorog2p and is not needed by normal tests or runtime installation.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from kokorog2p.th.g2p import ThaiG2P
from kokorog2p.th.model_profile import TARGET_MODEL, validate_output
from kokorog2p.th.normalizer import ThaiNormalizer


def _load_cases(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _reference_results(
    reference_dir: Path, cases: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    adapter = reference_dir / "benchmark_adapter.py"
    if not adapter.is_file():
        raise SystemExit(
            f"Reference adapter not found: {adapter}. Provide a pinned checkout with "
            "benchmark_adapter.py accepting JSONL on stdin."
        )
    completed = subprocess.run(
        [sys.executable, str(adapter)],
        input="".join(json.dumps(case, ensure_ascii=False) + "\n" for case in cases),
        text=True,
        capture_output=True,
        cwd=reference_dir,
        check=True,
    )
    return {
        str(item["id"]): item for item in map(json.loads, completed.stdout.splitlines())
    }


def run(reference_dir: Path, cases_path: Path) -> dict[str, Any]:
    cases = _load_cases(cases_path)
    reference = _reference_results(reference_dir, cases)
    g2p = ThaiG2P()
    normalizer = ThaiNormalizer()
    rows: list[dict[str, Any]] = []
    for case in cases:
        source = str(case["source"])
        phonemes = g2p.phonemize(source)
        valid, invalid = validate_output(phonemes)
        clean = normalizer(source)
        oracle = reference.get(str(case["id"]), {})
        rows.append(
            {
                "id": case["id"],
                "source": source,
                "category": case.get("category", "uncategorized"),
                "reference_normalized": oracle.get("normalized"),
                "clean_room_normalized": clean,
                "reference_phonemes": oracle.get("phonemes"),
                "clean_room_phonemes": phonemes,
                "exact_match": oracle.get("phonemes") == phonemes,
                "model_valid": valid,
                "invalid_symbols": invalid,
                "reference_drops": oracle.get("drops", []),
                "clean_room_warnings": list(g2p.warnings) + list(normalizer.warnings),
            }
        )
    exact = sum(row["exact_match"] for row in rows)
    valid = sum(row["model_valid"] for row in rows)
    silent_drops = sum(
        bool(row["reference_phonemes"]) and not row["clean_room_phonemes"]
        for row in rows
    )
    return {
        "target_model": TARGET_MODEL,
        "reference_dir": str(reference_dir),
        "cases": rows,
        "summary": {
            "case_count": len(rows),
            "exact_phoneme_matches": exact,
            "model_valid_count": valid,
            "silent_lexical_drop_count": silent_drops,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = (
        json.dumps(run(args.reference_dir, args.cases), ensure_ascii=False, indent=2)
        + "\n"
    )
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
