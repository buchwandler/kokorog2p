"""Optional offline-safe Arabic differential benchmark.

An oracle must be supplied explicitly by a maintainer. This script never imports,
downloads, or executes an external reference implementation automatically.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kokorog2p import get_g2p


def load_inputs(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset", type=Path, help="Text file with independently curated MSA inputs"
    )
    parser.add_argument("--output", type=Path, help="Write clean-room results as JSON")
    parser.add_argument(
        "--oracle-results",
        type=Path,
        help=(
            "Optional precomputed oracle JSON; no oracle code is loaded by this script"
        ),
    )
    args = parser.parse_args()

    inputs = load_inputs(args.dataset)
    g2p = get_g2p("ar", diacritizer="none")
    clean_results = [
        {"input": text, "phonemes": g2p.phonemize(text)} for text in inputs
    ]
    report: dict[str, object] = {
        "inputs": len(inputs),
        "oracle": "provided-results" if args.oracle_results else "not-run",
        "clean_room_results": clean_results,
        "metrics": {},
        "categories": [],
    }
    if args.oracle_results:
        report["oracle_results"] = json.loads(
            args.oracle_results.read_text(encoding="utf-8")
        )
        report["categories"] = [
            "eSpeak/backend differences",
            "diacritizer differences",
            "cleanup differences",
            "source-normalization differences",
        ]
    if args.output:
        args.output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
