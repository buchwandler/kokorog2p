#!/usr/bin/env python3
"""Build and check the committed G2Lex runtime assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import g2lex

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "lexicons" / "manifest.toml"
LOCK_PATH = ROOT / "lexicons" / "lock.json"


def load_manifest() -> list[dict[str, Any]]:
    import tomllib

    with MANIFEST_PATH.open("rb") as stream:
        manifest = tomllib.load(stream)
    if manifest.get("schema_version") != 1:
        raise ValueError("lexicons/manifest.toml must use schema_version = 1")
    records = manifest.get("lexicon")
    if not isinstance(records, list) or not records:
        raise ValueError("lexicons/manifest.toml must define lexicon records")
    required = {
        "id",
        "language",
        "name",
        "kind",
        "source",
        "source_format",
        "asset",
        "case_aliases",
        "phoneme_encoding",
    }
    result = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not required <= record.keys():
            raise ValueError(f"invalid manifest record: {record!r}")
        lexicon_id = str(record["id"])
        if lexicon_id in seen:
            raise ValueError(f"duplicate manifest id: {lexicon_id}")
        seen.add(lexicon_id)
        if record["kind"] not in {"pronunciation", "membership"}:
            raise ValueError(f"unsupported lexicon kind for {lexicon_id}")
        result.append(record)
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_path(record: dict[str, Any]) -> Path:
    path = ROOT / str(record["source"])
    if not path.is_file():
        raise FileNotFoundError(f"missing canonical source: {path}")
    return path


def asset_path(record: dict[str, Any]) -> Path:
    return ROOT / str(record["asset"])


def validate_source(record: dict[str, Any]) -> tuple[Any, Path]:
    path = source_path(record)
    parsed = g2lex.read_typed_lexicon(
        path, format=str(record["source_format"]), source_id=str(record["id"])
    )
    values = tuple(parsed.entries.values())
    if record["kind"] == "membership":
        if not values or any(value is not g2lex.WORD_ONLY for value in values):
            raise ValueError(f"membership source is not WORD_ONLY: {path}")
    elif any(value is g2lex.WORD_ONLY for value in values):
        raise ValueError(f"pronunciation source contains WORD_ONLY: {path}")
    return parsed, path


def build_record(record: dict[str, Any], output: Path) -> dict[str, Any]:
    parsed, source = validate_source(record)
    packed = g2lex.pack_file(
        source,
        output,
        input_format=str(record["source_format"]),
        source_id=str(record["id"]),
        metadata={
            "lexicon_id": str(record["id"]),
            "language": str(record["language"]),
            "name": str(record["name"]),
            "kind": str(record["kind"]),
            "case_aliases": bool(record["case_aliases"]),
            "phoneme_encoding": str(record["phoneme_encoding"]),
        },
    )
    verification = g2lex.verify_file(
        source, output, input_format=str(record["source_format"])
    )
    if not verification.get("lossless"):
        raise ValueError(
            f"independent verification failed for {record['id']}: {verification}"
        )
    result = {
        "source_sha256": sha256(source),
        "logical_sha256": str(packed["logical_sha256"]),
        "asset_sha256": sha256(output),
        "entry_count": int(packed["asset_entry_count"]),
        "asset_bytes": output.stat().st_size,
    }
    print(
        f"{record['id']}: source={source} source_bytes={source.stat().st_size} "
        f"source_entries={len(parsed)} source_sha256={result['source_sha256']} "
        f"asset={record['asset']} asset_bytes={result['asset_bytes']} "
        f"asset_entries={result['entry_count']} "
        f"logical_sha256={result['logical_sha256']} "
        f"asset_sha256={result['asset_sha256']} verification=lossless"
    )
    return result


def selected_records(
    records: list[dict[str, Any]], lexicon_id: str | None
) -> list[dict[str, Any]]:
    if lexicon_id is None:
        return records
    selected = [record for record in records if record["id"] == lexicon_id]
    if not selected:
        valid = ", ".join(str(record["id"]) for record in records)
        raise ValueError(f"unknown lexicon id {lexicon_id!r}; valid ids: {valid}")
    return selected


def build_all(
    records: list[dict[str, Any]], *, lexicon_id: str | None = None
) -> dict[str, Any]:
    lock: dict[str, Any] = {
        "schema_version": 1,
        "g2lex_version": g2lex.__version__,
        "assets": {},
    }
    existing = {}
    if LOCK_PATH.is_file():
        existing = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        if isinstance(existing, dict):
            lock["assets"].update(existing.get("assets", {}))
    for record in selected_records(records, lexicon_id):
        destination = asset_path(record)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix=f".{destination.stem}.", dir=destination.parent
        ) as temp:
            built = build_record(record, Path(temp) / destination.name)
            os.replace(Path(temp) / destination.name, destination)
        lock["assets"][str(record["id"])] = built
    if lexicon_id is None:
        lock["assets"] = {
            str(record["id"]): lock["assets"][str(record["id"])] for record in records
        }
        LOCK_PATH.write_text(
            json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    return lock


def check(records: list[dict[str, Any]]) -> None:
    if not LOCK_PATH.is_file():
        raise ValueError(f"missing lock file: {LOCK_PATH}")
    expected = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if (
        expected.get("schema_version") != 1
        or expected.get("g2lex_version") != g2lex.__version__
    ):
        raise ValueError("lock schema or G2Lex version does not match the build")
    actual_assets = expected.get("assets", {})
    if set(actual_assets) != {str(record["id"]) for record in records}:
        raise ValueError("lock assets do not match the manifest")
    for record in records:
        destination = asset_path(record)
        if not destination.is_file():
            raise ValueError(f"missing generated asset: {destination}")
        with tempfile.TemporaryDirectory(prefix=f".{destination.stem}.") as temp:
            built = build_record(record, Path(temp) / destination.name)
            if built != actual_assets[str(record["id"])]:
                raise ValueError(
                    f"generated metadata differs for {record['id']}: "
                    f"expected={actual_assets[str(record['id'])]!r} actual={built!r}"
                )
        if sha256(destination) != actual_assets[str(record["id"])]["asset_sha256"]:
            raise ValueError(f"committed asset hash differs for {record['id']}")
    print("G2Lex asset check passed; checkout was not modified.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="build every manifest record")
    group.add_argument("--id", help="build one manifest record")
    group.add_argument(
        "--check", action="store_true", help="rebuild in temporary files and compare"
    )
    args = parser.parse_args()
    records = load_manifest()
    if args.check:
        check(records)
    else:
        build_all(records, lexicon_id=args.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
