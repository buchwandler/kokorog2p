#!/usr/bin/env python3
"""Explicitly download pinned German experiment sources."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .lexlab.download import download_source
    from .lexlab.sources import load_manifest
except ImportError:  # direct script execution
    from lexlab.download import download_source
    from lexlab.sources import load_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Comma-separated source IDs")
    parser.add_argument(
        "--download", action="store_true", help="Required explicit network opt-in"
    )
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    if not args.download:
        parser.error("refusing network access: pass --download explicitly")
    specs = load_manifest()
    for source_id in (item.strip() for item in args.source.split(",")):
        if source_id == "builtin":
            print("builtin is packaged locally; no download required")
            continue
        try:
            path = download_source(specs[source_id], cache_dir=args.cache_dir)
        except (KeyError, OSError, ValueError) as exc:
            parser.error(str(exc))
        print(f"{source_id}\t{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
