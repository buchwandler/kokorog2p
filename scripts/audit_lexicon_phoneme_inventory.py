#!/usr/bin/env python3
"""Audit a packaged pronunciation asset against the German Kokoro vocabulary."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import g2lex

from kokorog2p.de.g2p import normalize_to_kokoro
from kokorog2p.lexicons.registry import get_lexicon_spec
from kokorog2p.vocab import get_vocab


def _unsupported_sequences(value: str, vocabulary: set[str]) -> tuple[str, ...]:
    sequences: list[str] = []
    current: list[str] = []
    for char in value:
        if char not in vocabulary:
            current.append(char)
        elif current:
            sequences.append("".join(current))
            current = []
    if current:
        sequences.append("".join(current))
    return tuple(sequences)


def audit(asset: Path) -> dict[str, object]:
    vocabulary = set(get_vocab())
    raw_characters: Counter[str] = Counter()
    normalized_characters: Counter[str] = Counter()
    raw_sequences: Counter[str] = Counter()
    normalized_sequences: Counter[str] = Counter()
    entry_count = variant_count = raw_affected_entries = normalized_affected_entries = 0
    raw_affected_variants = normalized_affected_variants = 0

    lexicon = g2lex.open(asset)
    try:
        for value in lexicon.values():
            entry_count += 1
            entry_raw_affected = entry_normalized_affected = False
            for pronunciation in g2lex.pronunciation_variants(value):
                variant_count += 1
                raw_bad = _unsupported_sequences(pronunciation, vocabulary)
                normalized = normalize_to_kokoro(
                    pronunciation, use_tie_replacement=True
                )
                normalized_bad = _unsupported_sequences(normalized, vocabulary)
                if raw_bad:
                    raw_affected_variants += 1
                    entry_raw_affected = True
                    raw_characters.update(
                        char for sequence in raw_bad for char in sequence
                    )
                    raw_sequences.update(raw_bad)
                if normalized_bad:
                    normalized_affected_variants += 1
                    entry_normalized_affected = True
                    normalized_characters.update(
                        char for sequence in normalized_bad for char in sequence
                    )
                    normalized_sequences.update(normalized_bad)
            raw_affected_entries += int(entry_raw_affected)
            normalized_affected_entries += int(entry_normalized_affected)
    finally:
        lexicon.close()

    return {
        "asset": str(asset),
        "entry_count": entry_count,
        "variant_count": variant_count,
        "raw_unsupported_characters": dict(sorted(raw_characters.items())),
        "normalized_unsupported_characters": dict(
            sorted(normalized_characters.items())
        ),
        "top_raw_offending_sequences": [
            {"sequence": sequence, "count": count}
            for sequence, count in sorted(
                raw_sequences.items(), key=lambda item: (-item[1], item[0])
            )[:20]
        ],
        "top_normalized_offending_sequences": [
            {"sequence": sequence, "count": count}
            for sequence, count in sorted(
                normalized_sequences.items(), key=lambda item: (-item[1], item[0])
            )[:20]
        ],
        "raw_affected_entries": raw_affected_entries,
        "raw_affected_variants": raw_affected_variants,
        "normalized_affected_entries": normalized_affected_entries,
        "normalized_affected_variants": normalized_affected_variants,
        "ok": not normalized_characters,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="registered lexicon id")
    args = parser.parse_args()
    spec = get_lexicon_spec("de-de", args.id.rsplit(":", 1)[-1])
    asset = Path("kokorog2p/lexicons/data") / spec.resource
    report = audit(asset)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
