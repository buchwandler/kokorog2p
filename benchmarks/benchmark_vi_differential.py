"""Manifest-only differential benchmark for Vietnamese frontends.

External systems are optional and diagnostic. They never replace curated gold.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from kokorog2p.vi import VietnameseG2P


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    path = Path(__file__).parent.parent / "tests" / "data" / "vi_gold.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    g2p = VietnameseG2P(foreign_fallback="none", strict=True)
    rows = []
    for case in cases:
        clean = g2p.phonemize(str(case["text"]))
        rows.append(
            {
                "input": case["text"],
                "clean_room": clean,
                "gold": case["expected"],
                "decision": clean == case["expected"],
                "notes": (
                    "Curated gold is authoritative; external engines are "
                    "diagnostic only."
                ),
            }
        )
    result = {
        "dialect": "vi-vn-north",
        "cases": rows,
        "comparators": [],
        "gold_source": "tests/data/vi_gold.json",
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Vietnamese differential cases: {len(rows)}")
        print(f"Curated matches: {sum(row['decision'] for row in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()
