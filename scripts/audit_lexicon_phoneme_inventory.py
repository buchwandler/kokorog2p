#!/usr/bin/env python3
"""Audit a packaged pronunciation asset at the German consumer boundary."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import g2lex

from kokorog2p.de.g2p import normalize_internal
from kokorog2p.lexicons.registry import get_lexicon_spec
from kokorog2p.vocab import get_vocab

_MAX_EXAMPLES = 3
_MAX_TOP = 20


def _unsupported_sequences(value: str, vocabulary: set[str]) -> tuple[str, ...]:
    """Return contiguous unsupported runs without modifying the input."""
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


def _top(counter: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"sequence": sequence, "count": count}
        for sequence, count in sorted(
            counter.items(), key=lambda item: (-item[1], item[0])
        )[:_MAX_TOP]
    ]


def audit(asset: Path, *, vocabulary: set[str] | None = None) -> dict[str, object]:
    """Audit every pronunciation variant and its selected first variant.

    The normalizer preserves unhandled material in ``value`` and classifies it in
    ``unsupported``.  Consequently this audit never infers safety from a string
    that has already been filtered.
    """
    target = set(get_vocab()) if vocabulary is None else set(vocabulary)
    raw_characters: Counter[str] = Counter()
    source_non_direct: Counter[str] = Counter()
    mapped: Counter[str] = Counter()
    ignored: Counter[str] = Counter()
    unhandled: Counter[str] = Counter()
    normalized_bad: Counter[str] = Counter()
    changed_variants = 0
    entry_count = variant_count = 0
    raw_affected_entries = normalized_affected_entries = 0
    raw_affected_variants = normalized_affected_variants = 0
    first_unhandled_variants = 0
    first_empty_entries = 0
    normalized_empty_variants = 0
    representative_words: dict[str, list[str]] = defaultdict(list)
    first_variant_words: dict[str, list[str]] = defaultdict(list)

    lexicon = g2lex.open(asset)
    try:
        for word, value in lexicon.items():
            entry_count += 1
            variants = tuple(g2lex.pronunciation_variants(value))
            if not variants:
                continue
            entry_raw_affected = False
            entry_normalized_affected = False
            for variant_index, pronunciation in enumerate(variants):
                variant_count += 1
                raw = str(pronunciation)
                raw_characters.update(raw)
                result = normalize_internal(
                    raw,
                    vocabulary=target,
                    use_tie_replacement=True,
                )
                replacements = result.replacements
                for source, _target in replacements:
                    mapped[source] += 1
                    source_non_direct[source] += 1
                for mark in result.ignored:
                    ignored[mark] += 1
                    source_non_direct[mark] += 1
                if result.unsupported:
                    raw_affected_variants += 1
                    entry_raw_affected = True
                    for sequence in result.unsupported:
                        unhandled[sequence] += 1
                        source_non_direct[sequence] += 1
                        if len(representative_words[sequence]) < _MAX_EXAMPLES:
                            representative_words[sequence].append(str(word))
                        if variant_index == 0:
                            first_variant_words[sequence].append(str(word))
                if result.value != raw:
                    changed_variants += 1
                output_bad = _unsupported_sequences(result.value, target)
                if output_bad:
                    normalized_affected_variants += 1
                    entry_normalized_affected = True
                    normalized_bad.update(output_bad)
                if not result.value:
                    normalized_empty_variants += 1
                if variant_index == 0 and (result.unsupported or not result.value):
                    first_unhandled_variants += int(bool(result.unsupported))
                    first_empty_entries += int(not result.value)
            raw_affected_entries += int(entry_raw_affected)
            normalized_affected_entries += int(entry_normalized_affected)
    finally:
        lexicon.close()

    unhandled_examples = {
        sequence: sorted(set(words))[:_MAX_EXAMPLES]
        for sequence, words in sorted(representative_words.items())
    }
    first_examples = {
        sequence: sorted(set(words))[:_MAX_EXAMPLES]
        for sequence, words in sorted(first_variant_words.items())
    }
    return {
        "asset": str(asset),
        "entry_count": entry_count,
        "variant_count": variant_count,
        "raw_source_inventory": dict(sorted(raw_characters.items())),
        "raw_unsupported_characters": dict(sorted(unhandled.items())),
        "source_non_direct_sequences": _top(source_non_direct),
        "mapped_sequences": _top(mapped),
        "ignored_sequences": _top(ignored),
        "unhandled_sequences": _top(unhandled),
        "unhandled_examples": unhandled_examples,
        "first_unhandled_examples": first_examples,
        "normalized_unsupported_characters": dict(sorted(normalized_bad.items())),
        "top_raw_offending_sequences": _top(unhandled),
        "top_normalized_offending_sequences": _top(normalized_bad),
        "raw_affected_entries": raw_affected_entries,
        "raw_affected_variants": raw_affected_variants,
        "normalized_affected_entries": normalized_affected_entries,
        "normalized_affected_variants": normalized_affected_variants,
        "first_variants_with_unhandled_material": first_unhandled_variants,
        "entries_with_empty_first_pronunciation": first_empty_entries,
        "normalized_empty_variants": normalized_empty_variants,
        "changed_variants": changed_variants,
        "ok": not (
            unhandled
            or normalized_bad
            or normalized_empty_variants
            or first_empty_entries
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="registered lexicon id")
    parser.add_argument(
        "--json", type=Path, dest="json_path", help="write the report as JSON"
    )
    args = parser.parse_args()
    spec = get_lexicon_spec("de-de", args.id.rsplit(":", 1)[-1])
    asset = Path("kokorog2p/lexicons/data") / spec.resource
    report = audit(asset)
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(serialized)
    if args.json_path:
        args.json_path.parent.mkdir(parents=True, exist_ok=True)
        args.json_path.write_text(serialized + "\n", encoding="utf-8")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
