"""Strict parsers for the source formats."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .model import ParsedLexicon, PronunciationRecord, SourceInfo


class LexiconFormatError(ValueError):
    """Raised when a source does not conform to its declared format."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_with_bytes(
    source: SourceInfo, data: bytes, path: Path | None = None
) -> SourceInfo:
    return SourceInfo(
        source.source_id,
        source.revision,
        sha256_bytes(data),
        source.license,
        source.provenance_status,
        source.parser_version,
        source.view_version,
        source.format,
        str(path) if path else source.path,
        len(data),
    )


def parse_tsv_text(
    text: str, source: SourceInfo, *, path: Path | None = None
) -> ParsedLexicon:
    """Parse a headerless two-column TSV without stripping record content."""
    entries: dict[str, list[PronunciationRecord]] = {}
    physical_lines = 0
    # splitlines(keepends=True) retains a final non-newline record and line numbers.
    for line_number, line in enumerate(text.splitlines(keepends=True), 1):
        physical_lines += 1
        fields = line.rstrip("\r\n").split("\t")
        if len(fields) != 2:
            raise LexiconFormatError(
                f"{path or source.source_id}:{line_number}: "
                f"expected 2 tab-separated fields, got {len(fields)}"
            )
        word, ipa = fields
        if not word:
            raise LexiconFormatError(
                f"{path or source.source_id}:{line_number}: empty spelling"
            )
        entries.setdefault(word, []).append(PronunciationRecord(ipa, line_number))
    if text and not physical_lines:
        physical_lines = 1
    parsed = ParsedLexicon(
        _source_with_bytes(source, text.encode("utf-8"), path),
        {word: tuple(records) for word, records in entries.items()},
        physical_lines,
    )
    parsed.metadata.update(_tsv_metadata(parsed))
    return parsed


def parse_tsv(path: Path, source: SourceInfo) -> ParsedLexicon:
    data = path.read_bytes()
    return parse_tsv_text(data.decode("utf-8"), source, path=path)


def parse_json_bytes(
    data: bytes, source: SourceInfo, *, path: Path | None = None
) -> ParsedLexicon:
    try:
        value: Any = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LexiconFormatError(
            f"{path or source.source_id}: invalid UTF-8 JSON: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise LexiconFormatError(
            f"{path or source.source_id}: JSON root must be an object"
        )
    entries: dict[str, tuple[PronunciationRecord, ...]] = {}
    for word, ipa in value.items():
        if not isinstance(word, str):
            raise LexiconFormatError(
                f"{path or source.source_id}: JSON keys must be strings"
            )
        if not word:
            raise LexiconFormatError(f"{path or source.source_id}: empty spelling")
        if not isinstance(ipa, str):
            raise LexiconFormatError(
                f"{path or source.source_id}: value for {word!r} must be a string"
            )
        entries[word] = (PronunciationRecord(ipa),)
    parsed = ParsedLexicon(
        _source_with_bytes(source, data, path), entries, len(entries)
    )
    parsed.metadata.update(_json_metadata(parsed))
    return parsed


def parse_json(path: Path, source: SourceInfo) -> ParsedLexicon:
    return parse_json_bytes(path.read_bytes(), source, path=path)


def _tsv_metadata(parsed: ParsedLexicon) -> dict[str, object]:
    records = list(parsed.iter_records())
    duplicate_rows = sum(
        count - 1
        for count in Counter((word, record.ipa) for word, record in records).values()
        if count > 1
    )
    return {
        "physical_lines": parsed.physical_rows,
        "unique_spellings": len(parsed.entries),
        "pronunciation_variants": sum(
            len(values) for values in parsed.entries.values()
        ),
        "words_with_multiple_pronunciations": sum(
            len(values) > 1 for values in parsed.entries.values()
        ),
        "maximum_variants": max(
            (len(values) for values in parsed.entries.values()), default=0
        ),
        "duplicate_identical_rows": duplicate_rows,
        "empty_words": 0,
        "empty_ipa": sum(not record.ipa for _, record in records),
        "rows_with_spaces_in_ipa": sum(" " in record.ipa for _, record in records),
        "rows_with_tabs_in_ipa": sum("\t" in record.ipa for _, record in records),
        "non_nfc_words": sum(
            unicodedata.normalize("NFC", word) != word for word, _ in records
        ),
        "non_nfc_ipa": sum(
            unicodedata.normalize("NFC", record.ipa) != record.ipa
            for _, record in records
        ),
    }


def _json_metadata(parsed: ParsedLexicon) -> dict[str, object]:
    return {
        "physical_lines": parsed.physical_rows,
        "unique_spellings": len(parsed.entries),
        "pronunciation_variants": sum(
            len(values) for values in parsed.entries.values()
        ),
        "duplicate_identical_rows": 0,
        "non_nfc_words": sum(
            unicodedata.normalize("NFC", word) != word for word in parsed.entries
        ),
        "non_nfc_ipa": sum(
            unicodedata.normalize("NFC", record.ipa) != record.ipa
            for _, record in parsed.iter_records()
        ),
    }


def parse_path(path: Path, source: SourceInfo) -> ParsedLexicon:
    return (
        parse_json(path, source)
        if source.format in {"json_single", "json"} or path.suffix.lower() == ".json"
        else parse_tsv(path, source)
    )
