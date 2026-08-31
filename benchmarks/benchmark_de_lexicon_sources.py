#!/usr/bin/env python3
"""Compare pinned German lexicon sources using Kokoro's consumer semantics.

Inputs are explicit local G2Lex assets or source files; no source is downloaded
by this benchmark. The Kokoro pronunciation view lives in
``benchmarks.lexicon_quality.de`` rather than in G2Lex.
"""

from __future__ import annotations

import argparse
import itertools
import time
import json
from pathlib import Path

import g2lex
from g2lex.layers import LayeredLexicon, LexiconLayer

from benchmarks.crane_test_data import (
    create_benchmark_g2p,
    extract_pronunciation,
    load_test_tsv,
    load_vocab,
    normalize_reference_ipa,
    resolve_data_root,
)
from benchmarks.lexicon_quality.de import to_kokoro_view
from kokorog2p.de.g2p import normalize_internal


def _load_source(spec: str):
    name, location = spec.split("=", 1)
    path_text, separator, format_name = location.rpartition(":")
    formats = {
        "tsv",
        "lxc-tsv",
        "json",
        "json-map",
        "jsonl",
        "cmudict",
        "mfa",
        "pls",
        "words",
        "ipa-tsv",
    }
    if separator and format_name in formats:
        path, input_format = Path(path_text), format_name
    else:
        path, input_format = Path(location), "auto"
    if path.suffix.lower() == ".g2lex":
        return name, g2lex.open(path)
    return name, g2lex.read_typed_lexicon(path, format=input_format, source_id=name)


def _resident_memory() -> int | None:
    try:
        import psutil
    except ImportError:
        return None
    return psutil.Process().memory_info().rss
def _crane_data(root: Path | None, download: bool):
    from benchmarks.crane_test_data import LANGUAGES

    config = LANGUAGES["de_DE"]
    data_root = resolve_data_root(root, download=download, configs=(config,))
    vocab = load_vocab(data_root / "g2p/kokoro_vocab.json")
    return load_test_tsv(data_root / config.test_path), vocab, normalize_reference_ipa


def _source_id(source, fallback: str) -> str:
    info = getattr(source, "source", None)
    if isinstance(info, dict):
        return str(info.get("source_id", fallback))
    return str(getattr(info, "source_id", fallback))


def _variants(source, word: str) -> tuple[str, ...]:
    lookup_all = getattr(source, "lookup_all", None)
    if lookup_all is not None:
        return tuple(lookup_all(word) or lookup_all(word.lower()))
    value = source.get(word) or source.get(word.lower())
    return tuple(g2lex.pronunciation_variants(value)) if value is not None else ()


def _consumer_view(source_name: str, value: str, vocab) -> tuple[str, bool]:
    if source_name in {"espeak", "olaph"} or source_name.startswith("cstr_"):
        normalized = normalize_internal(value, vocabulary=set(vocab), use_tie_replacement=True)
        return normalized.value if normalized.valid else "", normalized.valid
    converted = to_kokoro_view(source_name, value, vocab=vocab)
    return converted, True


def score_source(source, entries, vocab, normalizer, *, source_name: str):
    selected = oracle = covered = 0
    usable_first = invalid_first = 0
    expected_values, actual_values = [], []
    rows = []
    lookup_started = time.perf_counter()
    conversion_source = _source_id(source, source_name)
    for entry in entries:
        expected = normalizer(entry.expected_raw_ipa, language="de_DE", vocab=vocab)
        variants = _variants(source, entry.word)
        views_with_validity = tuple(
            _consumer_view(conversion_source, value, vocab) for value in variants
        )
        views = tuple(view for view, _valid in views_with_validity)
        if variants and views_with_validity[0][1]:
            usable_first += 1
        elif variants:
            invalid_first += 1
        actual = views[0] if views else ""
        covered += bool(variants)
        selected += actual == expected
        oracle += expected in views
        expected_values.append(expected)
        actual_values.append(actual)
        rows.append(
            {
                "word": entry.word,
                "covered": bool(variants),
                "variant_count": len(variants),
                "selected_exact": actual == expected,
                "oracle_exact": expected in views,
            }
        )
    lookup_elapsed = time.perf_counter() - lookup_started
    return {
        "source": source_name,
        "entries": len(entries),
        "coverage": covered / len(entries) if entries else 0.0,
        "usable_first_pronunciation_count": usable_first,
        "invalid_first_pronunciation_count": invalid_first,
        "target_vocabulary_validity": usable_first / covered if covered else 0.0,
        "lookup_throughput_words_per_second": len(entries) / lookup_elapsed if lookup_elapsed else 0.0,
        "selected_exact_match_rate": selected / len(entries) if entries else 0.0,
        "oracle_variant_exact_match_rate": oracle / len(entries) if entries else 0.0,
        "invalid_or_empty_outputs": sum(not value for value in actual_values),
        "rows": rows,
    }


def score_full_pipeline(source, entries, vocab, normalizer, *, source_name: str):
    fallback = create_benchmark_g2p("de_DE")
    values, expected_values = [], []
    fallback_rows = 0
    for entry in entries:
        expected_values.append(
            normalizer(entry.expected_raw_ipa, language="de_DE", vocab=vocab)
        )
        variants = _variants(source, entry.word)
        if variants:
            value, valid = _consumer_view(
                _source_id(source, source_name), variants[0], vocab
            )
            if valid:
                values.append(value)
                continue
        fallback_rows += 1
        try:
            values.append(extract_pronunciation(fallback(entry.word)))
        except (OSError, RuntimeError, ValueError):
            values.append("")
    exact = sum(
        left == right for left, right in zip(expected_values, values, strict=True)
    )
    return {
        "entries": len(values),
        "coverage": sum(bool(value) for value in values) / len(values)
        if values
        else 0.0,
        "selected_exact_match_rate": exact / len(values) if values else 0.0,
        "fallback_rows": fallback_rows,
        "invalid_or_empty_outputs": sum(not value for value in values),
    }


def score_cascade(sources, entries, vocab, normalizer):
    words = [entry.word for entry in entries]
    references = {
        entry.word: (normalizer(entry.expected_raw_ipa, language="de_DE", vocab=vocab),)
        for entry in entries
    }
    layers = [LexiconLayer(name, source, {}) for name, source in sources]
    return evaluate_quality_cascade(layers, words, references, vocab)

def evaluate_quality_cascade(layers, words, references, vocab):
    layered = LayeredLexicon(layers)
    selected = oracle = covered = 0
    for word in words:
        hit = layered.get_hit(word)
        if hit is None:
            continue
        covered += 1
        selected_value = g2lex.first_pronunciation(hit.value) or ""
        selected_value, _valid = _consumer_view(hit.name, selected_value, vocab)
        selected += selected_value == references[word][0]
        for layer in layers:
            value = g2lex.first_pronunciation(layer.lexicon.get(word)) or ""
            value, _valid = _consumer_view(layer.name, value, vocab)
            if value == references[word][0]:
                oracle += 1
                break
    total = len(words)
    return {
        "layers": [layer.name for layer in layers],
        "entries": total,
        "coverage": covered / total if total else 0.0,
        "selected_exact_match_rate": selected / total if total else 0.0,
        "oracle_variant_exact_match_rate": oracle / total if total else 0.0,
        "fallback_rows": total - covered,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", action="append", required=True, metavar="NAME=PATH[:FORMAT]"
    )
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
    sources = []
    source_metrics = {}
    for source_spec in args.source:
        started = time.perf_counter()
        before = _resident_memory()
        loaded = _load_source(source_spec)
        name, source = loaded
        after = _resident_memory()
        location = source_spec.split("=", 1)[1]
        path_text, separator, format_name = location.rpartition(":")
        path = Path(path_text) if separator and format_name in {"ipa-tsv", "tsv", "g2lex"} else Path(location)
        sources.append(loaded)
        source_metrics[name] = {
            "cold_open_ms": (time.perf_counter() - started) * 1000,
            "resident_memory_delta_bytes": after - before if before is not None and after is not None else None,
            "asset_size_bytes": path.stat().st_size if path.suffix == ".g2lex" else None,
        }
    results = []
    for name, source in sources:
        scored = score_source(source, entries, vocab, normalizer, source_name=name)
        scored.update(source_metrics[name])
        results.append(
            {
                "source": name,
                **scored,
                "full_pipeline": score_full_pipeline(
                    source, entries, vocab, normalizer, source_name=name
                ),
            }
        )
    cascades = [
        score_cascade([sources[index] for index in order], entries, vocab, normalizer)
        for order in itertools.permutations(range(len(sources)))
    ]
    for order, result in zip(
        itertools.permutations([name for name, _ in sources]), cascades, strict=True
    ):
        result["configuration"] = " -> ".join(order)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema": 1,
                "fixture": "crane-local-ai/test-data",
                "sources": results,
                "cascades": cascades,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
