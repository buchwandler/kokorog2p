#!/usr/bin/env python3
"""Analyze source statistics, overlaps, reachability, and baseline storage."""

from __future__ import annotations

import argparse
import gzip
import lzma
import platform
import time
from pathlib import Path

try:
    from .lexlab.keys import casing_collisions, unicode_statistics
    from .lexlab.overlap import all_pair_metrics
    from .lexlab.reports import source_dict, write_json, write_tsv
    from .lexlab.sources import load_source
except ImportError:  # direct script execution
    from lexlab.keys import casing_collisions, unicode_statistics
    from lexlab.overlap import all_pair_metrics
    from lexlab.reports import source_dict, write_json, write_tsv
    from lexlab.sources import load_source


def _reachability(source):
    rows = []
    try:
        from kokorog2p.de.normalizer import GermanNormalizer
        from kokorog2p.pipeline.tokenizer import RegexTokenizer

        normalizer = GermanNormalizer()
        tokenizer = RegexTokenizer(lang="de")
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        return [
            {"source": source.source.source_id, "error": f"{type(exc).__name__}: {exc}"}
        ]
    for word in source.words:
        try:
            normalized = normalizer(word)
            tokens = tokenizer.tokenize(normalized)
            token_texts = tuple(token.text for token in tokens)
            if not token_texts:
                classification = "EMPTY_AFTER_NORMALIZATION"
                key = ""
            elif len(token_texts) > 1 or token_texts[0] != normalized:
                classification = (
                    "SPLIT_MULTIPLE_TOKENS"
                    if len(token_texts) > 1
                    else "NORMALIZED_SINGLE_TOKEN_CHANGED"
                )
                key = token_texts[0].lower() if len(token_texts) == 1 else ""
            elif token_texts[0].isalnum() or any(
                char.isalpha() for char in token_texts[0]
            ):
                classification = "DIRECT_SINGLE_TOKEN"
                key = token_texts[0].lower()
            else:
                classification = "PUNCT_ONLY_OR_INVALID"
                key = ""
            rows.append(
                {
                    "source": source.source.source_id,
                    "source_word": word,
                    "normalized_text": normalized,
                    "tokens": "|".join(token_texts),
                    "classification": classification,
                    "lookup_key": key,
                }
            )
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            rows.append(
                {
                    "source": source.source.source_id,
                    "source_word": word,
                    "normalized_text": "",
                    "tokens": "",
                    "classification": "ERROR",
                    "lookup_key": "",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return rows


def _canonical_tsv(source) -> bytes:
    return "".join(
        f"{word}\t{record.ipa}\n"
        for word, record in sorted(
            source.iter_records(), key=lambda item: (item[0], item[1].line_number or 0)
        )
    ).encode("utf-8")


def analyze(
    source_ids: list[str],
    data_root: Path | None,
    output: Path,
    *,
    details: str = "sample",
    conflict_limit: int = 10_000,
    reachability: bool = True,
    summary_only: bool = False,
) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    loaded = {
        source_id: load_source(source_id, data_root=data_root)
        for source_id in source_ids
    }
    source_rows = []
    key_rows = []
    variant_rows = []
    unicode_rows = []
    reach_rows = []
    baseline_rows = []
    for source_id, source in loaded.items():
        source_rows.append(
            {
                **source_dict(source.source),
                **source.metadata,
                "source": source_id,
                "pronunciation_variants": sum(len(v) for v in source.entries.values()),
            }
        )
        if not summary_only and details != "none":
            collisions = casing_collisions(source)
            rows = [
                {
                    "source": source_id,
                    "key_type": key_type,
                    "key": key,
                    "spellings": "|".join(words),
                }
                for key_type, groups in collisions.items()
                for key, words in groups.items()
            ]
            key_rows.extend(rows if details == "full" else rows[:1000])
        variant_rows.append(
            {
                "source": source_id,
                "unique_words": len(source.entries),
                "physical_rows": source.physical_rows,
                "variants": sum(len(v) for v in source.entries.values()),
                "multi_variant_words": sum(len(v) > 1 for v in source.entries.values()),
                "max_variants": max(
                    (len(v) for v in source.entries.values()), default=0
                ),
                "duplicate_identical_rows": source.metadata.get(
                    "duplicate_identical_rows", 0
                ),
            }
        )
        unicode_rows.append(
            {
                "source": source_id,
                **{
                    key: value
                    for key, value in unicode_statistics(source).items()
                    if not isinstance(value, dict)
                },
            }
        )
        if reachability and not summary_only:
            reach_rows.extend(_reachability(source))
        started = time.perf_counter()
        canonical = _canonical_tsv(source)
        elapsed = time.perf_counter() - started
        gzip_bytes = gzip.compress(canonical, mtime=0)
        xz_bytes = lzma.compress(
            canonical, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64
        )
        baseline_rows.append(
            {
                "source": source_id,
                "source_bytes": source.source.size_bytes,
                "canonical_bytes": len(canonical),
                "gzip_bytes": len(gzip_bytes),
                "xz_bytes": len(xz_bytes),
                "serialization_seconds": elapsed,
                "python": platform.python_version(),
            }
        )
    pairs = all_pair_metrics(loaded)
    for pair in pairs:
        pair["conflicts"] = pair.get("conflicts", [])[:conflict_limit]
    write_json(
        output / "summary.json",
        {
            "schema": 1,
            "python": platform.python_version(),
            "options": {
                "details": details,
                "conflict_limit": conflict_limit,
                "reachability": reachability,
                "summary_only": summary_only,
            },
            "sources": source_rows,
            "pairs": pairs,
            "reachability": {
                source_id: sum(
                    row.get("classification") == "DIRECT_SINGLE_TOKEN"
                    for row in reach_rows
                    if row.get("source") == source_id
                )
                for source_id in loaded
            },
        },
    )
    write_tsv(output / "sources.tsv", source_rows)
    write_tsv(
        output / "key_stats.tsv", key_rows, ["source", "key_type", "key", "spellings"]
    )
    write_tsv(output / "variant_stats.tsv", variant_rows)
    write_tsv(output / "unicode_stats.tsv", unicode_rows)
    write_tsv(
        output / "casing_collisions.tsv",
        key_rows,
        ["source", "key_type", "key", "spellings"],
    )
    write_tsv(
        output / "overlap_words.tsv",
        [
            {
                "source_a": row["source_a"],
                "source_b": row["source_b"],
                "exact_intersection": row["exact_spelling_intersection"],
            }
            for row in pairs
        ],
    )
    write_tsv(
        output / "pronunciation_agreement.tsv",
        [
            {key: value for key, value in row.items() if key != "conflicts"}
            for row in pairs
        ],
    )
    write_tsv(
        output / "conflicts.tsv",
        [
            {"source_a": pair["source_a"], "source_b": pair["source_b"], **conflict}
            for pair in pairs
            for conflict in pair["conflicts"]
        ],
    )
    write_tsv(output / "reachability.tsv", reach_rows)
    write_tsv(output / "baseline.tsv", baseline_rows)
    write_json(
        output / "provenance.json",
        {source_id: source_dict(source.source) for source_id, source in loaded.items()},
    )
    (output / "README.md").write_text(
        "Generated source analysis. Raw source records were not normalized; "
        "Kokoro views are analysis-only.\n",
        encoding="utf-8",
    )
    return {"sources": source_rows, "pairs": pairs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Comma-separated source IDs")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--details",
        choices=("none", "sample", "full"),
        default="sample",
    )
    parser.add_argument("--conflict-limit", type=int, default=10_000)
    parser.add_argument("--no-reachability-rows", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()
    analyze(
        [item.strip() for item in args.source.split(",")],
        args.data_root,
        args.output,
        details=args.details,
        conflict_limit=args.conflict_limit,
        reachability=not args.no_reachability_rows,
        summary_only=args.summary_only,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
