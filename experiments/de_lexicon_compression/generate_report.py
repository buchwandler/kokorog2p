#!/usr/bin/env python3
"""Render a human-readable final research report from generated JSON reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def generate(
    source_analysis: Path | None,
    quality: Path | None,
    matrix: Path | None,
    output: Path,
) -> None:
    analysis = _load(source_analysis) if source_analysis else {}
    quality_data = _load(quality) if quality else {}
    matrix_data = _load(matrix) if matrix else {}
    lines = [
        "# German Multi-Lexicon Compression Experiment",
        "",
        "This report is generated from explicitly pinned experiment outputs. Missing sections mean the corresponding opt-in run was not available.",
        "",
        "## 1. Executive summary",
        "",
        "Sources are evaluated independently. A result is called lossless only when the reloaded decoder reproduces every ordered raw pronunciation tuple exactly.",
        "",
        "## 2. Source provenance and licenses",
        "",
    ]
    for source in analysis.get("sources", []):
        lines.append(
            f"- **{source.get('source', source.get('source_id'))}**: revision `{source.get('revision')}`, SHA256 `{source.get('sha256')}`, license `{source.get('license')}`, status `{source.get('provenance_status')}`."
        )
    lines.extend(["", "## 3. Source sizes and variant statistics", ""])
    for source in analysis.get("sources", []):
        lines.append(
            f"- {source.get('source')}: {source.get('unique_spellings', 0)} unique spellings, {source.get('pronunciation_variants', 0)} variants, {source.get('size_bytes', 0)} bytes."
        )
    lines.extend(
        [
            "",
            "## 4. Casing/Unicode findings",
            "",
            "See `casing_collisions.tsv` and `unicode_stats.tsv`; raw source codepoints are preserved.",
            "",
            "## 5. Runtime reachability",
            "",
            json.dumps(analysis.get("reachability", {}), sort_keys=True),
            "",
            "## 6. Pairwise overlap and pronunciation conflicts",
            "",
        ]
    )
    for pair in analysis.get("pairs", []):
        lines.append(
            f"- {pair.get('source_a')} vs {pair.get('source_b')}: exact overlap {pair.get('exact_spelling_intersection', 0)}, raw agreement {pair.get('exact_raw_pronunciation_agreement', 0)}, Kokoro-view agreement {pair.get('kokoro_view_any_variant_agreement', 0)}."
        )
    lines.extend(
        [
            "",
            "## 7. Held-out G2P quality",
            "",
            "```json",
            json.dumps(quality_data, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## 8. Baseline gzip/xz results",
            "",
            "See the source-analysis `baseline.tsv` output.",
            "",
            "## 9. Exact two-part compression",
            "",
            "## 10. Exact multipart compression",
            "",
            "```json",
            json.dumps(matrix_data, ensure_ascii=False, indent=2, sort_keys=True),
            "```",
            "",
            "## 11. Failure taxonomy",
            "",
            "Failures are diagnostic only; no approximate match authorizes deletion.",
            "",
            "## 12. Runtime/RAM cost",
            "",
            "See each run's `runtime.json`.",
            "",
            "## 13. Cross-source sharing potential",
            "",
            "Cross-source sharing is deferred until independent source semantics and licensing are reviewed.",
            "",
            "## 14. Recommendation for production architecture",
            "",
            "Adopt explicit ordered source selection only if measured held-out quality and reachability justify the additional source and its licensing obligations.",
            "",
            "## 15. Recommendation on exact join rules",
            "",
            "Do not add linguistic join rules until C3 failures are measured and every rule is independently verified.",
            "",
            "## 16. Recommendation on neural follow-up",
            "",
            "Use only the exactly factorized residual as a possible later neural-G2P research input; approximation is not compression evidence.",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-analysis", type=Path)
    parser.add_argument("--quality", type=Path)
    parser.add_argument("--matrix", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generate(args.source_analysis, args.quality, args.matrix, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
