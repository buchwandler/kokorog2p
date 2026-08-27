#!/usr/bin/env python3
"""Compare source coverage and pronunciation quality on the pinned Crane fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .lexlab.kokoro_view import to_kokoro_view
    from .lexlab.metrics import cer
    from .lexlab.reports import write_json
    from .lexlab.sources import load_source
except ImportError:  # direct script execution
    from lexlab.kokoro_view import to_kokoro_view
    from lexlab.metrics import cer
    from lexlab.reports import write_json
    from lexlab.sources import load_source


def _crane_data(root: Path | None, download: bool):
    from benchmarks.crane_test_data import (
        LANGUAGES,
        load_test_tsv,
        load_vocab,
        normalize_reference_ipa,
        resolve_data_root,
    )

    config = LANGUAGES["de_DE"]
    data_root = resolve_data_root(root, download=download, configs=(config,))
    vocab = load_vocab(data_root / "g2p/kokoro_vocab.json")
    entries = load_test_tsv(data_root / config.test_path)
    return entries, vocab, normalize_reference_ipa


def score_source(source, entries, vocab, normalizer):
    covered = selected_exact = oracle_exact = 0
    selected_values: list[str] = []
    expected_values: list[str] = []
    fallback_count = 0
    rows = []
    for entry in entries:
        expected = normalizer(entry.expected_raw_ipa, language="de_DE", vocab=vocab)
        variants = source.lookup_all(entry.word)
        if not variants:
            key = entry.word.lower()
            variants = source.lookup_all(key)
        if variants:
            covered += 1
        views = tuple(
            to_kokoro_view(source.source.source_id, value, vocab=vocab)
            for value in variants
        )
        selected = views[0] if views else ""
        selected_values.append(selected)
        expected_values.append(expected)
        selected_match = selected == expected
        oracle_match = expected in views
        selected_exact += selected_match
        oracle_exact += oracle_match
        rows.append(
            {
                "word": entry.word,
                "covered": bool(variants),
                "variant_count": len(variants),
                "selected_exact": selected_match,
                "oracle_exact": oracle_match,
                "selected_cer": cer((expected,), (selected,)),
            }
        )
        if not variants:
            fallback_count += 1
    return {
        "source": source.source.source_id,
        "entries": len(entries),
        "coverage": covered / len(entries) if entries else 0.0,
        "selected_exact_match_rate": selected_exact / len(entries) if entries else 0.0,
        "oracle_variant_exact_match_rate": oracle_exact / len(entries)
        if entries
        else 0.0,
        "selected_cer": cer(tuple(expected_values), tuple(selected_values)),
        "invalid_or_empty_outputs": sum(not value for value in selected_values),
        "fallback_rows": fallback_count,
        "rows": rows,
    }


def score_full_pipeline(source, entries, vocab, normalizer):
    """Score source lookup plus the normal German fallback profile."""
    try:
        from benchmarks.crane_test_data import (
            create_benchmark_g2p,
            extract_pronunciation,
        )

        fallback = create_benchmark_g2p("de_DE")
    except Exception as exc:  # optional eSpeak/runtime dependencies
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    values = []
    expected_values = []
    fallback_rows = 0
    errors = 0
    for entry in entries:
        expected = normalizer(entry.expected_raw_ipa, language="de_DE", vocab=vocab)
        variants = source.lookup_all(entry.word) or source.lookup_all(
            entry.word.lower()
        )
        if variants:
            actual = to_kokoro_view(source.source.source_id, variants[0], vocab=vocab)
        else:
            fallback_rows += 1
            try:
                actual = extract_pronunciation(fallback(entry.word))
            except Exception:
                actual = ""
                errors += 1
        expected_values.append(expected)
        values.append(actual)
    exact = sum(
        left == right for left, right in zip(expected_values, values, strict=True)
    )
    return {
        "available": True,
        "entries": len(entries),
        "coverage": sum(bool(value) for value in values) / len(values)
        if values
        else 0.0,
        "selected_exact_match_rate": exact / len(values) if values else 0.0,
        "oracle_variant_exact_match_rate": exact / len(values) if values else 0.0,
        "selected_cer": cer(tuple(expected_values), tuple(values)),
        "invalid_or_empty_outputs": sum(not value for value in values),
        "fallback_rows": fallback_rows,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--download-crane-test-data", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    entries, vocab, normalizer = _crane_data(
        args.data_root, args.download_crane_test_data
    )
    if args.limit is not None:
        entries = entries[: args.limit]
    results = []
    for source_id in (value.strip() for value in args.sources.split(",")):
        source = load_source(source_id, data_root=args.data_root)
        score = score_source(source, entries, vocab, normalizer)
        score["full_pipeline"] = score_full_pipeline(source, entries, vocab, normalizer)
        results.append(score)
    output = {
        "schema": 1,
        "fixture": "crane-local-ai/test-data",
        "revision": "19b6ea610af45d9258a3957c7a22694280bdf145",
        "sources": results,
    }
    write_json(args.output, output)
    print(
        json.dumps({"sources": len(results), "entries": len(entries)}, sort_keys=True)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
