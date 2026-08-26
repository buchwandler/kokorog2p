"""Reproducible smoke benchmark for native Vietnamese G2P."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from kokorog2p.vi import VietnameseG2P


def load_cases() -> list[dict[str, object]]:
    path = Path(__file__).parent.parent / "tests" / "data" / "vi_gold.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=100)
    args = parser.parse_args()
    cases = load_cases()
    g2p = VietnameseG2P(foreign_fallback="none", strict=True)
    words = [str(case["text"]) for case in cases]
    start = time.perf_counter()
    for _ in range(args.repeat):
        for word in words:
            g2p.phonemize(word)
    elapsed = time.perf_counter() - start
    count = len(words) * args.repeat
    print(
        json.dumps(
            {
                "syllables": count,
                "seconds": elapsed,
                "syllables_per_second": count / elapsed,
            }
        )
    )


if __name__ == "__main__":
    main()
