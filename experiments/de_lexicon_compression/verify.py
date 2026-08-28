#!/usr/bin/env python3
"""Independently reload and verify a lookup-semantic asset."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

try:
    from .lexlab.compact import verify_lookup
    from .lexlab.reports import write_json
    from .lexlab.serializer import ASSET_SCHEMA, load_asset
    from .lexlab.sources import load_source
except ImportError:  # direct script execution
    from lexlab.compact import verify_lookup
    from lexlab.reports import write_json
    from lexlab.serializer import ASSET_SCHEMA, load_asset
    from lexlab.sources import load_source


def verify(
    run: Path,
    *,
    source_id: str | None = None,
    data_root: Path | None = None,
    sample_limit: int = 100,
) -> dict[str, object]:
    asset_path = run / "compressed.asset" if run.is_dir() else run
    asset_bytes = asset_path.read_bytes()
    asset = load_asset(asset_path)
    source_name = source_id or asset.source.source_id
    source = load_source(source_name, data_root=data_root)
    report = (
        asset.verify_report(source, sample_limit=sample_limit)
        if hasattr(asset, "verify_report")
        else verify_lookup(asset, source, sample_limit=sample_limit)
    )
    result = {
        "schema_version": ASSET_SCHEMA,
        "compressor_version": asset.metadata.get("compressor_version", "1"),
        "parser_version": asset.source.parser_version,
        "view_version": asset.source.view_version,
        "source_sha256": source.source.sha256,
        "asset_sha256": hashlib.sha256(asset_bytes).hexdigest(),
        "lossless_contract": asset.metadata.get("lossless_contract", "lookup-semantic"),
        "words_checked": len(source.entries),
        "variants_checked": sum(len(values) for values in source.entries.values()),
        "exact_words": (
            len(source.entries)
            - len(report["missing_words"])
            - report["pronunciation_mismatches"]
        ),
        **report,
    }
    if run.is_dir():
        write_json(run / "independent-verification.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--sample-limit", type=int, default=100)
    args = parser.parse_args()
    result = verify(
        args.run,
        source_id=args.source,
        data_root=args.data_root,
        sample_limit=args.sample_limit,
    )
    print(f"Words checked:       {result['words_checked']}")
    print(f"Variants checked:    {result['variants_checked']}")
    print(f"Exact word tuples:   {result['exact_words']}")
    print(f"Missing words:       {len(result['missing_words'])}")
    print(f"Extra words:         {len(result['extra_words'])}")
    print(f"Pronunciation mismatches: {result['pronunciation_mismatches']}")
    print(f"Failures:            {result['failures']}")
    return 0 if result["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
