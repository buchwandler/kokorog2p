#!/usr/bin/env python3
"""Build and check the committed G2Lex runtime assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from importlib.metadata import version as distribution_version
from pathlib import Path
from typing import Any

import g2lex

# The runtime module may fall back to a placeholder when loaded from a wheel;
# the distribution metadata is the version used to build and lock the asset.
G2LEX_VERSION = distribution_version("g2lex")
ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "lexicons" / "manifest.toml"
LOCK_PATH = ROOT / "lexicons" / "lock.json"


def _validate_repository_relative_path(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"manifest field {field!r} must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(
            f"manifest field {field!r} must be repository-relative: {value!r}"
        )
    return value


def load_manifest() -> list[dict[str, Any]]:  # noqa: C901
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
    supported_encodings = {"kokoro-v1", "ipa", "none"}
    provenance_fields = {
        "provider",
        "revision",
        "source_url",
        "license_expression",
        "license_url",
        "attribution",
    }
    result: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_language_names: set[tuple[str, str]] = set()
    seen_assets: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not required <= record.keys():
            raise ValueError(f"invalid manifest record: {record!r}")
        string_fields = required - {"case_aliases"}
        if any(
            not isinstance(record[field], str) or not record[field].strip()
            for field in string_fields
        ):
            raise ValueError(
                f"manifest record has invalid required field types: {record!r}"
            )
        lexicon_id = str(record["id"])
        language = str(record["language"])
        name = str(record["name"])
        if lexicon_id in seen_ids:
            raise ValueError(f"duplicate manifest id: {lexicon_id}")
        seen_ids.add(lexicon_id)
        language_name = (language, name)
        if language_name in seen_language_names:
            raise ValueError(f"duplicate manifest language/name: {language_name!r}")
        seen_language_names.add(language_name)
        if lexicon_id != f"{language}:{name}":
            raise ValueError(
                f"manifest id must be '{language}:{name}', got {lexicon_id!r}"
            )
        _validate_repository_relative_path(record["source"], "source")
        asset = _validate_repository_relative_path(record["asset"], "asset")
        asset_basename = Path(asset).name
        existing_basenames = {Path(item["asset"]).name for item in result}
        if asset in seen_assets or asset_basename in existing_basenames:
            raise ValueError(f"duplicate manifest asset: {asset}")
        seen_assets.add(asset)
        if not isinstance(record["case_aliases"], bool):
            raise TypeError(f"case_aliases must be boolean for {lexicon_id}")
        if record["kind"] not in {"pronunciation", "membership"}:
            raise ValueError(f"unsupported lexicon kind for {lexicon_id}")
        if record["phoneme_encoding"] not in supported_encodings:
            raise ValueError(f"unsupported phoneme encoding for {lexicon_id}")
        if record.get("consumer_invalid_policy", "error") not in {"error", "fallback"}:
            raise ValueError(f"unsupported consumer invalid policy for {lexicon_id}")
        for optional in ("default_priority", "rating"):
            if optional in record and (
                not isinstance(record[optional], int)
                or isinstance(record[optional], bool)
            ):
                raise TypeError(f"{optional} must be an integer for {lexicon_id}")
        if "rating" in record and not 0 <= record["rating"] <= 5:
            raise ValueError(f"rating must be between 0 and 5 for {lexicon_id}")
        if "source_sha256" in record and (
            not isinstance(record["source_sha256"], str)
            or len(record["source_sha256"]) != 64
        ):
            raise ValueError(
                f"source_sha256 must be a 64-character hex string for {lexicon_id}"
            )
        if "source_size" in record and (
            not isinstance(record["source_size"], int)
            or isinstance(record["source_size"], bool)
            or record["source_size"] < 0
        ):
            raise ValueError(
                f"source_size must be a non-negative integer for {lexicon_id}"
            )
        if "third_party" in record and not isinstance(record["third_party"], bool):
            raise TypeError(f"third_party must be boolean for {lexicon_id}")
        if record.get("provider") is not None or record.get("third_party") is True:
            missing = sorted(provenance_fields - record.keys())
            if missing:
                raise ValueError(
                    f"third-party record {lexicon_id} is missing provenance: "
                    f"{', '.join(missing)}"
                )
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


REGISTRY_PATH = ROOT / "kokorog2p" / "lexicons" / "_generated_registry.py"


def python_literal(value: object) -> str:
    return json.dumps(value) if isinstance(value, str) else repr(value)


def registry_text(records: list[dict[str, Any]]) -> str:
    """Render manifest metadata as deterministic importable Python."""
    fields = (
        "id",
        "language",
        "name",
        "resource",
        "kind",
        "rating",
        "case_aliases",
        "phoneme_encoding",
        "consumer_invalid_policy",
        "default_priority",
        "provider",
        "revision",
        "source_url",
        "license_expression",
        "license_url",
        "attribution",
    )
    lines = [
        '"""Generated from lexicons/manifest.toml; do not edit manually."""',
        "",
        "from __future__ import annotations",
        "",
        "GENERATED_LEXICONS = (",
    ]
    for record in records:
        lines.append("    {")
        for field in fields:
            if field == "resource" and "asset" in record:
                value = Path(str(record["asset"])).name
            elif field in record:
                value = record[field]
            else:
                continue
            rendered = f"        {python_literal(field)}: {python_literal(value)},"
            if field == "attribution":
                rendered += "  # noqa: E501"
            lines.append(rendered)
        lines.append("    },")
    lines.extend((")", ""))
    return "\n".join(lines)


def write_registry(records: list[dict[str, Any]], path: Path = REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(registry_text(records), encoding="utf-8")


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
    expected_source_hash = record.get("source_sha256")
    if expected_source_hash is not None and sha256(source) != expected_source_hash:
        raise ValueError(f"source SHA-256 differs from manifest for {record['id']}")
    expected_source_size = record.get("source_size")
    if (
        expected_source_size is not None
        and source.stat().st_size != expected_source_size
    ):
        raise ValueError(f"source size differs from manifest for {record['id']}")
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
            "consumer_invalid_policy": str(record.get("consumer_invalid_policy", "error")),
            **{
                key: record[key]
                for key in (
                    "provider",
                    "revision",
                    "source_url",
                    "license_expression",
                    "license_url",
                    "attribution",
                )
                if key in record
            },
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
        "generator": f"g2lex {G2LEX_VERSION}",
        "phoneme_encoding": str(record["phoneme_encoding"]),
        "consumer_invalid_policy": str(record.get("consumer_invalid_policy", "error")),
        **{
            key: record[key]
            for key in (
                "revision",
                "source_url",
                "license_expression",
                "license_url",
                "attribution",
            )
            if key in record
        },
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
        "g2lex_version": G2LEX_VERSION,
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
        write_registry(records)
    return lock


def check(records: list[dict[str, Any]]) -> None:
    if not LOCK_PATH.is_file():
        raise ValueError(f"missing lock file: {LOCK_PATH}")
    expected = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if (
        expected.get("schema_version") != 1
        or expected.get("g2lex_version") != G2LEX_VERSION
    ):
        raise ValueError("lock schema or G2Lex version does not match the build")
    with tempfile.TemporaryDirectory(prefix=".generated-registry.") as temp:
        generated = Path(temp) / REGISTRY_PATH.name
        write_registry(records, generated)
        committed = (
            REGISTRY_PATH.read_text(encoding="utf-8")
            if REGISTRY_PATH.is_file()
            else None
        )
        if committed != generated.read_text(encoding="utf-8"):
            raise ValueError("generated runtime registry differs from manifest")
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
