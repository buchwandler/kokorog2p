#!/usr/bin/env python3
"""Independently reload and verify an exact source-semantic asset."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .lexlab.reports import write_json
    from .lexlab.serializer import load_asset
    from .lexlab.sources import load_source
except ImportError:  # direct script execution
    from lexlab.reports import write_json
    from lexlab.serializer import load_asset
    from lexlab.sources import load_source


def verify(
    run: Path, *, source_id: str | None = None, data_root: Path | None = None
) -> dict[str, object]:
    asset = load_asset(run / "compressed.asset" if run.is_dir() else run)
    source_name = source_id or asset.source.source_id
    source = load_source(source_name, data_root=data_root)
    failures = []
    variants = 0
    for word in source.words:
        expected = source.lookup_all(word)
        actual = asset.lookup_all(word)
        variants += len(expected)
        if expected != actual:
            failures.append({"word": word, "expected": expected, "actual": actual})
    result = {
        "words_checked": len(source.entries),
        "variants_checked": variants,
        "exact_words": len(source.entries) - len(failures),
        "failures": len(failures),
        "failure_rows": failures,
    }
    if run.is_dir():
        write_json(run / "independent-verification.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args()
    result = verify(args.run, source_id=args.source, data_root=args.data_root)
    print(f"Words checked:       {result['words_checked']}")
    print(f"Variants checked:    {result['variants_checked']}")
    print(f"Exact word tuples:   {result['exact_words']}")
    print(f"Failures:             {result['failures']}")
    return 0 if result["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
