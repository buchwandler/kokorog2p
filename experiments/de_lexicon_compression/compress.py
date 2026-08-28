#!/usr/bin/env python3
"""Create a deterministic exact-composition asset for one source."""

from __future__ import annotations

import argparse
import platform
import resource
import time
from dataclasses import asdict
from pathlib import Path

try:
    from .lexlab.compact import (
        deserialize_compact,
        serialize_compact,
        verify_lookup,
    )
    from .lexlab.compressor import compress_lexicon
    from .lexlab.metrics import compare_compression_layers
    from .lexlab.p4 import serialize_front_coded
    from .lexlab.reports import source_dict, write_json, write_tsv
    from .lexlab.serializer import serialize, serialize_canonical, write_asset
    from .lexlab.sources import load_source
except ImportError:  # direct script execution
    from lexlab.compact import deserialize_compact, serialize_compact, verify_lookup
    from lexlab.compressor import compress_lexicon
    from lexlab.metrics import compare_compression_layers
    from lexlab.p4 import serialize_front_coded
    from lexlab.reports import source_dict, write_json, write_tsv
    from lexlab.serializer import serialize, serialize_canonical, write_asset
    from lexlab.sources import load_source


def _rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if platform.system() == "Darwin" else value * 1024)


def run(
    source_id: str,
    mode: str,
    output: Path,
    *,
    data_root: Path | None = None,
    max_states: int = 100_000,
    max_variant_product: int = 100_000,
    failure_sample_limit: int = 100,
    full_failures: bool = False,
):
    source = load_source(source_id, data_root=data_root)
    compact_modes = {
        "exact-multipart-ids",
        "ipa-intern",
        "ipa-repair-macros",
        "front-coded",
    }
    effective_mode = (
        "exact-multipart" if mode in compact_modes or mode == "exact-linkers" else mode
    )
    rss_before = _rss_bytes()
    result = compress_lexicon(
        source,
        mode=effective_mode,
        max_states=max_states,
        max_variant_product=max_variant_product,
        failure_sample_limit=failure_sample_limit,
        full_failures=full_failures,
    )
    rss_after_compress = _rss_bytes()
    output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    if mode == "front-coded":
        asset = serialize_front_coded(result.compressed)
        (output / "compressed.asset").write_bytes(asset)
        decoded = deserialize_compact(asset)
        asset_bytes = len(asset)
        verification = verify_lookup(decoded, source)
    elif mode in compact_modes:
        asset = serialize_compact(result.compressed, mode)
        (output / "compressed.asset").write_bytes(asset)
        decoded = deserialize_compact(asset)
        asset_bytes = len(asset)
        verification = verify_lookup(decoded, source)
    else:
        asset_bytes = write_asset(output / "compressed.asset", result.compressed)
        asset = serialize(result.compressed)
        verification = result.compressed.verify_report(source)
    verification_seconds = time.perf_counter() - started
    rss_after = _rss_bytes()
    canonical = serialize_canonical(source)
    (output / "baseline-canonical.json").write_bytes(canonical)
    layers = compare_compression_layers(canonical, asset)
    summary = {
        "schema": 1,
        "source": source_id,
        "source_revision": source.source.revision,
        "source_sha256": source.source.sha256,
        "lossless_contract": "lookup-semantic",
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
        "canonical_baseline_bytes": len(canonical),
        "failure_counts": result.failure_counts,
        "verification": verification,
        "performance": {
            "compression_seconds": result.elapsed_seconds,
            "verification_seconds": verification_seconds,
            "rss_before_bytes": rss_before,
            "rss_after_compress_bytes": rss_after_compress,
            "rss_after_bytes": rss_after,
            "peak_rss_bytes": max(rss_before, rss_after_compress, rss_after),
        },
        "instrumentation": {
            key: value for key, value in asdict(result.metrics).items()
        },
        "compression_layers": layers,
        "provenance": source_dict(source.source),
        "platform": platform.platform(),
        "python": platform.python_version(),
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
            {
                "word": word,
                "components": "|".join(components),
            }
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
    write_json(output / "failure_counts.json", result.failure_counts)
    write_tsv(output / "component_usage.tsv", result.component_usage)
    write_tsv(output / "derivation_depth.tsv", result.derivation_depth)
    write_tsv(
        output / "ambiguity.tsv",
        result.ambiguity,
        [
            "word",
            "spelling_candidate_count",
            "exact_candidate_count",
            "selected_components",
            "alternative_exact_components",
            "selection_reason",
        ],
    )
    write_json(output / "verification.json", verification)
    write_tsv(
        output / "verification.tsv",
        [
            {
                "word": word,
                "status": ("fail" if word in verification["missing_words"] else "pass"),
            }
            for word in source.words
        ],
        ["word", "status"],
    )
    write_tsv(
        output / "size_breakdown.tsv",
        [
            {"section": "asset", "bytes": asset_bytes},
            {"section": "canonical_baseline", "bytes": len(canonical)},
            *[
                {"section": key, "bytes": value}
                for key, value in layers.items()
                if key.startswith(("asset_", "baseline_"))
            ],
        ],
        ["section", "bytes"],
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument(
        "--mode",
        choices=(
            "baseline",
            "baseline-canonical",
            "exact-two-part",
            "exact-multipart",
            "exact-multipart-ids",
            "ipa-intern",
            "ipa-repair-macros",
            "front-coded",
            "exact-linkers",
        ),
        required=True,
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--max-states", type=int, default=100_000)
    parser.add_argument("--max-variant-product", type=int, default=100_000)
    parser.add_argument("--failure-sample-limit", type=int, default=100)
    parser.add_argument("--full-failures", action="store_true")
    args = parser.parse_args()
    run(
        args.source,
        args.mode,
        args.output,
        data_root=args.data_root,
        max_states=args.max_states,
        max_variant_product=args.max_variant_product,
        failure_sample_limit=args.failure_sample_limit,
        full_failures=args.full_failures,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
