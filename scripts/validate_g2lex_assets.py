#!/usr/bin/env python3
"""Validate canonical G2Lex assets without changing the checkout."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import Any

import g2lex

G2LEX_VERSION = distribution_version("g2lex")
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
    return records


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_value(value: object, record: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    kind = record["kind"]
    if kind == "membership":
        if value is not g2lex.WORD_ONLY:
            errors.append("membership value is not WORD_ONLY")
        return errors
    if value is g2lex.WORD_ONLY:
        errors.append("pronunciation value is WORD_ONLY")
    elif (
        isinstance(value, str)
        or isinstance(value, tuple)
        and all(isinstance(item, str) for item in value)
    ):
        pass
    elif isinstance(value, g2lex.TaggedValue):
        for tag, selected in value.items:
            if selected is not None and not (
                isinstance(selected, str)
                or isinstance(selected, tuple)
                and all(isinstance(item, str) for item in selected)
            ):
                errors.append(f"invalid selector value for {tag!r}")
    else:
        errors.append(f"unsupported value type {type(value).__name__}")
    return errors


def validate_record(
    record: Mapping[str, Any], lock: Mapping[str, Any]
) -> dict[str, Any]:
    from g2lex import inspect_file, read_typed_lexicon, verify_file

    identifier = str(record["id"])
    source = ROOT / str(record["source"])
    asset = ROOT / str(record["asset"])
    errors: list[str] = []
    locked = lock.get("assets", {}).get(identifier)
    if not isinstance(locked, Mapping):
        return {"id": identifier, "ok": False, "errors": ["missing lock record"]}
    if not source.is_file():
        errors.append(f"missing source: {source}")
    if not asset.is_file():
        errors.append(f"missing asset: {asset}")
    if errors:
        return {"id": identifier, "ok": False, "errors": errors}

    try:
        parsed = read_typed_lexicon(
            source, format=str(record["source_format"]), source_id=identifier
        )
        source_hash = digest(source)
        asset_hash = digest(asset)
        report = verify_file(source, asset, input_format=str(record["source_format"]))
        metadata = inspect_file(asset)
        opened = g2lex.open(asset)
        try:
            value_errors = [
                f"{word}: {error}"
                for word, value in opened.items()
                for error in check_value(value, record)
            ]
            embedded_source = opened.metadata.get("source", {})
            embedded_source_hash = embedded_source.get(
                "source_sha256", embedded_source.get("sha256")
            )
            embedded_logical = opened.metadata.get("logical_sha256")
            embedded_count = opened.metadata.get("entry_count")
        finally:
            opened.close()
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return {
            "id": identifier,
            "ok": False,
            "errors": [f"validation exception: {exc}"],
        }

    if source_hash != locked.get("source_sha256"):
        errors.append("source SHA-256 differs from lock")
    if asset_hash != locked.get("asset_sha256"):
        errors.append("asset SHA-256 differs from lock")
    if parsed.logical_sha256 != locked.get("logical_sha256"):
        errors.append("logical SHA-256 differs from lock")
    if len(parsed) != locked.get("entry_count"):
        errors.append("source entry count differs from lock")
    if asset.stat().st_size != locked.get("asset_bytes"):
        errors.append("asset byte count differs from lock")
    if embedded_source_hash != source_hash:
        errors.append("embedded source SHA-256 differs from source")
    if embedded_logical != locked.get("logical_sha256"):
        errors.append("embedded logical SHA-256 differs from lock")
    if embedded_count != locked.get("entry_count"):
        errors.append("embedded entry count differs from lock")
    if not report.get("lossless"):
        errors.append(f"G2Lex lossless verification failed: {report}")
    errors.extend(value_errors)
    return {
        "id": identifier,
        "source": str(source.relative_to(ROOT)),
        "source_bytes": source.stat().st_size,
        "source_entries": len(parsed),
        "source_sha256": source_hash,
        "asset": str(asset.relative_to(ROOT)),
        "asset_bytes": asset.stat().st_size,
        "asset_entries": metadata.get("entry_count"),
        "logical_sha256": parsed.logical_sha256,
        "asset_sha256": asset_hash,
        "verification": "lossless" if report.get("lossless") else "failed",
        "ok": not errors,
        "errors": errors,
    }


def runtime_parity(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Run consumer parity hooks supplied by the migrated runtime modules."""
    from kokorog2p.lexicons.runtime import validate_runtime_parity

    return validate_runtime_parity(records, ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--all",
        action="store_true",
        help="validate every manifest record",
    )
    group.add_argument("--id", help="validate one manifest record")
    parser.add_argument("--runtime-parity", action="store_true")
    parser.add_argument("--json", type=Path, dest="json_path")
    args = parser.parse_args()
    if not MANIFEST_PATH.is_file() or not LOCK_PATH.is_file():
        raise SystemExit("manifest.toml and lock.json are required")
    all_records = load_manifest()
    records = (
        all_records
        if args.all
        else [record for record in all_records if record["id"] == args.id]
    )
    if not records:
        valid = ", ".join(str(record["id"]) for record in all_records)
        raise SystemExit(f"unknown lexicon id {args.id!r}; valid ids: {valid}")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "schema_version": 1,
        "g2lex_version": G2LEX_VERSION,
        "assets": [validate_record(record, lock) for record in records],
    }
    if args.runtime_parity:
        result["runtime_parity"] = runtime_parity(records)
    failures = [item for item in result["assets"] if not item["ok"]]
    failures.extend(
        item for item in result.get("runtime_parity", []) if not item.get("ok", False)
    )
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    for item in result["assets"]:
        status = "PASS" if item["ok"] else "FAIL"
        print(f"{status} {item['id']}: {item.get('verification', 'not checked')}")
        for error in item.get("errors", ()):
            print(f"  {error}")
    for item in result.get("runtime_parity", ()):
        status = "PASS" if item.get("ok") else "FAIL"
        print(f"{status} runtime parity {item.get('id', 'unknown')}")
        for error in item.get("errors", ()):
            print(f"  {error}")
    if failures:
        raise SystemExit(1)
    print("G2Lex asset validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
