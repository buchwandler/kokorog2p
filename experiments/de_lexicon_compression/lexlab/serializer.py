"""Deterministic JSON asset format for experiment runs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .decoder import CompressedLexicon
from .model import SourceInfo

ASSET_SCHEMA = 1


def _source_dict(source: SourceInfo) -> dict[str, Any]:
    value = asdict(source)
    # Absolute checkout/cache paths would make otherwise identical assets differ.
    value["path"] = Path(source.path).name if source.path else None
    return value


def asset_dict(compressed: CompressedLexicon) -> dict[str, Any]:
    return {
        "schema": ASSET_SCHEMA,
        "source": _source_dict(compressed.source),
        "metadata": dict(compressed.metadata),
        "atoms": {key: list(compressed.atoms[key]) for key in sorted(compressed.atoms)},
        "exceptions": {
            key: list(compressed.exceptions[key])
            for key in sorted(compressed.exceptions)
        },
        "derived": {
            key: list(compressed.derived[key]) for key in sorted(compressed.derived)
        },
    }


def canonical_asset_dict(source) -> dict[str, Any]:
    """Build the representation-equivalent direct lookup baseline."""
    return {
        "schema": 1,
        "kind": "baseline-canonical",
        "source": _source_dict(source.source),
        "entries": {
            word: list(source.lookup_all(word)) for word in sorted(source.words)
        },
    }


def serialize_canonical(source) -> bytes:
    return (
        json.dumps(
            canonical_asset_dict(source),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def serialize(compressed: CompressedLexicon) -> bytes:
    return (
        json.dumps(
            asset_dict(compressed),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_asset(path: Path, compressed: CompressedLexicon) -> int:
    data = serialize(compressed)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return len(data)


def deserialize(data: bytes):
    value = json.loads(data.decode("utf-8"))
    if value.get("schema") == 2:
        from .compact import deserialize_compact

        return deserialize_compact(data)
    if value.get("schema") != ASSET_SCHEMA:
        raise ValueError(f"unsupported asset schema: {value.get('schema')!r}")
    source = SourceInfo(**value["source"])
    return CompressedLexicon(
        source,
        {key: tuple(values) for key, values in value.get("atoms", {}).items()},
        {key: tuple(values) for key, values in value.get("exceptions", {}).items()},
        {key: tuple(values) for key, values in value.get("derived", {}).items()},
        dict(value.get("metadata", {})),
    )


def load_asset(path: Path) -> CompressedLexicon:
    return deserialize(path.read_bytes())
