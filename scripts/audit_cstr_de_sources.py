#!/usr/bin/env python3
"""Audit pinned CSTR German sources before generating runtime assets."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import g2lex
from build_g2lex_assets import ROOT, load_manifest

from kokorog2p.de.g2p import normalize_internal
from kokorog2p.vocab import get_vocab

_HEADERS = frozenset({"espeak_ipa", "ipa", "pronunciation"})


def _rejected_digest(pairs: list[tuple[str, str]]) -> str:
    payload = json.dumps(
        sorted(pairs), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def audit_source(record: dict[str, Any]) -> dict[str, object]:
    source = ROOT / str(record["source"])
    raw = source.read_bytes()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    header_rows_skipped = int(
        bool(lines)
        and len(lines[0].split("\t")) == 2
        and lines[0].split("\t")[0] == "word"
        and lines[0].split("\t")[1] in _HEADERS
    )
    missing_outer_delimiters = 0
    empty_words = 0
    empty_pronunciations = 0
    data_rows = 0
    for line_number, line in enumerate(lines, 1):
        if not line or line_number == 1 and header_rows_skipped:
            continue
        data_rows += 1
        fields = line.split("\t")
        if len(fields) != 2:
            continue
        word, pronunciation = fields
        empty_words += int(not word)
        empty_pronunciations += int(not pronunciation)
        missing_outer_delimiters += int(
            bool(pronunciation)
            and not (pronunciation.startswith("/") and pronunciation.endswith("/"))
        )

    parsed = g2lex.read_typed_lexicon(
        source, format=str(record["source_format"]), source_id=str(record["id"])
    )
    vocabulary = set(get_vocab())
    unsupported: Counter[str] = Counter()
    accepted = invalid = target_violations = 0
    rejected_pairs: list[tuple[str, str]] = []
    for word, value in parsed.entries.items():
        variants = tuple(g2lex.pronunciation_variants(value))
        if not variants:
            invalid += 1
            continue
        first = str(variants[0])
        result = normalize_internal(
            first, vocabulary=vocabulary, use_tie_replacement=True
        )
        for sequence in result.unsupported:
            unsupported[sequence] += 1
        has_target_violation = any(char not in vocabulary for char in result.value)
        if result.valid and result.value and not has_target_violation:
            accepted += 1
        else:
            invalid += 1
            target_violations += int(has_target_violation)
            rejected_pairs.append((str(word), first))

    return {
        "id": str(record["id"]),
        "raw_byte_size": len(raw),
        "raw_sha256": hashlib.sha256(raw).hexdigest(),
        "physical_rows": len(lines),
        "header_rows_skipped": header_rows_skipped,
        "logical_entries": len(parsed),
        "unique_keys": len(parsed.entries),
        "duplicate_rows": data_rows - len(parsed.entries),
        "multi_pronunciation_keys": sum(
            len(tuple(g2lex.pronunciation_variants(value))) > 1
            for value in parsed.entries.values()
        ),
        "empty_words": empty_words,
        "empty_pronunciations": empty_pronunciations,
        "missing_outer_delimiters": missing_outer_delimiters,
        "accepted_first_pronunciations": accepted,
        "invalid_first_pronunciations": invalid,
        "target_vocabulary_violations": target_violations,
        "unsupported_sequences": dict(sorted(unsupported.items())),
        "rejected_set_sha256": _rejected_digest(rejected_pairs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", action="append", required=True, dest="identifiers")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "lexicons" / "audits")
    args = parser.parse_args()
    records = {str(record["id"]): record for record in load_manifest()}
    for identifier in args.identifiers:
        if identifier not in records:
            raise SystemExit(f"unknown lexicon id {identifier!r}")
        report = audit_source(records[identifier])
        output = args.output_dir / f"{identifier.replace(':', '_')}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
