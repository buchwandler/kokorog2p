#!/usr/bin/env python3
"""Fetch the pinned CSTR German lexicon sources for maintainers."""

from __future__ import annotations

import argparse
import hashlib
import os
import tempfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "de-de:espeak": {
        "filename": "espeak_de.tsv",
        "revision": "eeac6ffc9271838fd63464a83d4b784ac75fc95b",
        "sha256": "190b62f1ddcf6616b62214173f05b09804635b170f75b9877eceab20b1624dbf",
        "size": 23829981,
    },
    "de-de:olaph": {
        "filename": "olaph_de.txt",
        "revision": "cedb4ada41a288549db36c53f9a1e6858a668624",
        "sha256": "aa70d85ce245c8a8f1db2cc109a0f3da6594eaba5b414a61bcd28f1ccc40ca46",
        "size": 41709849,
    },
}


def _url(record: dict[str, object]) -> str:
    return (
        "https://huggingface.co/datasets/cstr/g2p-dicts/resolve/"
        f"{record['revision']}/{record['filename']}"
    )


def _digest(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _verify(path: Path, record: dict[str, object]) -> None:
    actual_hash, actual_size = _digest(path)
    if actual_size != record["size"] or actual_hash != record["sha256"]:
        raise SystemExit(
            f"{path}: expected {record['size']} bytes/{record['sha256']}, "
            f"got {actual_size} bytes/{actual_hash}"
        )


def fetch(identifier: str) -> Path:
    record = SOURCES[identifier]
    destination = ROOT / "lexicons" / "sources" / "de" / str(record["filename"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            with urlopen(_url(record)) as response:
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
            _verify(temporary, record)
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    print(f"{identifier}: {destination} verified")
    return destination


def check(identifier: str) -> Path:
    destination = ROOT / "lexicons" / "sources" / "de" / str(SOURCES[identifier]["filename"])
    if not destination.is_file():
        raise SystemExit(f"missing source: {destination}")
    _verify(destination, SOURCES[identifier])
    print(f"{identifier}: {destination} verified")
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--id", choices=tuple(SOURCES))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    identifiers = tuple(SOURCES) if args.all else (args.id,)
    operation = check if args.check else fetch
    for identifier in identifiers:
        operation(identifier)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
