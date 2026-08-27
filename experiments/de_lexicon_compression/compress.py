#!/usr/bin/env python3
"""Create a deterministic exact-composition asset for one source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .lexlab.compressor import compress_lexicon
    from .lexlab.reports import source_dict, write_json, write_tsv
    from .lexlab.serializer import write_asset
    from .lexlab.sources import load_source
except ImportError:  # direct script execution
    from lexlab.compressor import compress_lexicon
    from lexlab.reports import source_dict, write_json, write_tsv
    from lexlab.serializer import write_asset
    from lexlab.sources import load_source


def run(
    source_id: str,
    mode: str,
    output: Path,
    *,
    data_root: Path | None = None,
    max_states: int = 100_000,
):
    source = load_source(source_id, data_root=data_root)
    result = compress_lexicon(source, mode=mode, max_states=max_states)
    output.mkdir(parents=True, exist_ok=True)
    asset_bytes = write_asset(output / "compressed.asset", result.compressed)
    verification = result.compressed.verify_against(source)
    summary = {
        "schema": 1,
        "source": source_id,
        "source_revision": source.source.revision,
        "source_sha256": source.source.sha256,
        "lossless_contract": "source-semantic",
        "compression_mode": mode,
        "physical_rows": source.physical_rows,
        "unique_words": len(source.entries),
        "pronunciation_variants": sum(
            len(values) for values in source.entries.values()
        ),
        "atom_words": len(result.compressed.atoms),
        "exception_words": len(result.compressed.exceptions),
        "derived_words": len(result.compressed.derived),
        "derived_variants": sum(
            len(source.lookup_all(word)) for word in result.compressed.derived
        ),
        "entry_reduction_rate": len(result.compressed.derived) / len(source.entries)
        if source.entries
        else 0.0,
        "source_bytes": source.source.size_bytes,
        "compressed_asset_bytes": asset_bytes,
        "compression_ratio": asset_bytes / source.source.size_bytes
        if source.source.size_bytes
        else 0.0,
        "verification": {
            "words_checked": len(source.entries),
            "variants_checked": sum(len(v) for v in source.entries.values()),
            "exact_words": len(source.entries) - len(verification),
            "failures": len(verification),
        },
        "performance": {
            "compression_seconds": result.elapsed_seconds,
            "verification_seconds": 0.0,
            "peak_rss_bytes": 0,
        },
        "instrumentation": {
            "candidate_atom_prefixes_tested": result.metrics.candidate_atom_prefixes_tested,
            "dp_states_visited": result.metrics.dp_states_visited,
            "cache_hits": result.metrics.cache_hits,
            "cache_hit_rate": result.metrics.cache_hit_rate,
            "max_decomposition_search_states": result.metrics.max_search_states_per_word,
        },
        "provenance": source_dict(source.source),
    }
    write_json(output / "summary.json", summary)
    write_tsv(
        output / "retained_atoms.tsv",
        [
            {"atom": word, "variants": "|".join(values)}
            for word, values in result.compressed.atoms.items()
        ],
        ["atom", "variants"],
    )
    write_tsv(
        output / "exceptions.tsv",
        [
            {"word": word, "variants": "|".join(values)}
            for word, values in result.compressed.exceptions.items()
        ],
        ["word", "variants"],
    )
    write_tsv(
        output / "derived.tsv",
        [
            {"word": word, "components": "|".join(components)}
            for word, components in result.compressed.derived.items()
        ],
        ["word", "components"],
    )
    write_tsv(
        output / "failures.tsv",
        result.failures,
        [
            "source",
            "word",
            "variant_index",
            "expected",
            "candidate",
            "components",
            "reason",
        ],
    )
    write_tsv(output / "component_usage.tsv", result.component_usage)
    write_tsv(output / "derivation_depth.tsv", result.derivation_depth)
    write_tsv(output / "ambiguity.tsv", [], ["word", "candidate_count", "selected"])
    write_json(
        output / "verification.json",
        {
            "words_checked": len(source.entries),
            "variants_checked": sum(len(v) for v in source.entries.values()),
            "exact_words": len(source.entries) - len(verification),
            "failures": list(verification),
        },
    )
    write_tsv(
        output / "verification.tsv",
        [
            {"word": word, "status": "fail" if word in verification else "pass"}
            for word in source.words
        ],
        ["word", "status"],
    )
    write_tsv(
        output / "size_breakdown.tsv",
        [
            {"section": "asset", "bytes": asset_bytes},
            {
                "section": "atoms",
                "bytes": len(
                    json.dumps(
                        result.compressed.atoms, ensure_ascii=False, sort_keys=True
                    ).encode()
                ),
            },
            {
                "section": "exceptions",
                "bytes": len(
                    json.dumps(
                        result.compressed.exceptions, ensure_ascii=False, sort_keys=True
                    ).encode()
                ),
            },
            {
                "section": "derived",
                "bytes": len(
                    json.dumps(
                        result.compressed.derived, ensure_ascii=False, sort_keys=True
                    ).encode()
                ),
            },
        ],
        ["section", "bytes"],
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument(
        "--mode",
        choices=("baseline", "exact-two-part", "exact-multipart"),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--max-states", type=int, default=100_000)
    args = parser.parse_args()
    run(
        args.source,
        args.mode,
        args.output,
        data_root=args.data_root,
        max_states=args.max_states,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
