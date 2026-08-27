"""Deterministic report and serialization helpers."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_tsv(
    path: Path, rows: Iterable[Mapping[str, Any]], fields: list[str] | None = None
) -> None:
    rows = list(rows)
    if fields is None:
        fields = list(rows[0]) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def source_dict(source: Any) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "revision": source.revision,
        "sha256": source.sha256,
        "license": source.license,
        "provenance_status": source.provenance_status,
        "parser_version": source.parser_version,
        "view_version": source.view_version,
        "format": source.format,
        "path": source.path,
        "size_bytes": source.size_bytes,
    }
