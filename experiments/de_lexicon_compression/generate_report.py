#!/usr/bin/env python3
"""Render a human-readable final research report from JSON reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _load(path: Path | None) -> dict:
    if path is None or not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def generate(
    source_analysis: Path | None,
    quality: Path | None,
    matrix: Path | None,
    output: Path,
) -> None:
    analysis = _load(source_analysis)
    quality_data = _load(quality)
    matrix_data = _load(matrix)
    lines = [
        "# German Multi-Lexicon Compression Experiment",
        "",
        "This report is generated only from explicitly pinned experiment outputs.",
        "Unavailable opt-in runs are not inferred from toy data.",
        "",
        "## 1. Executive summary",
        "",
        "A run is lookup-semantic lossless only when its complete key set",
        "and every ordered raw pronunciation tuple match after reload.",
        "Approximate pronunciation similarity never authorizes deletion.",
        "",
        "## 2. Provenance and reproducibility",
        "",
    ]
    for source in analysis.get("sources", []):
        lines.append(
            f"- **{source.get('source', source.get('source_id'))}**: "
            f"revision `{source.get('revision')}`, "
            f"SHA256 `{source.get('sha256')}`, license "
            f"`{source.get('license')}`, status "
            f"`{source.get('provenance_status')}`."
        )
    for row in matrix_data.get("rows", []):
        lines.append(
            f"- `{row.get('source')}/{row.get('mode')}`: source SHA256 "
            f"`{row.get('source_sha256')}`, Python `{row.get('python')}`, "
            f"platform `{row.get('platform')}`."
        )
    lines.extend(
        [
            "",
            "## 3. Source and quality findings",
            "",
            "```json",
            json.dumps(
                {"analysis": analysis, "quality": quality_data},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            "```",
            "",
            "## 4. Comparable storage results",
            "",
            "The primary distribution metric is net wheel-equivalent",
            "DEFLATE savings against the canonical runtime baseline.",
            "",
            "| Source | Mode | Installed | Wheel | Net wheel | Failures |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in matrix_data.get("rows", []):
        installed = row.get("asset_plain_bytes", row.get("asset_bytes"))
        lines.append(
            f"| {row.get('source')} | {row.get('mode')} | {installed} | "
            f"{row.get('asset_wheel_equivalent_deflate_bytes')} | "
            f"{row.get('net_wheel_equivalent_deflate_bytes_saved')} | "
            f"{row.get('verification_failures')} |"
        )
    lines.extend(
        [
            "",
            "## 5. Runtime and RAM",
            "",
            "See each run's `runtime.json` for atoms, exceptions, derived, misses,",
            "mixed workloads, cold load, normalized RSS, and baseline ratios.",
            "Empty categories must be marked unavailable, not fake words.",
            "",
            "## 6. Decision gates",
            "",
            "- Correctness: missing, extra, pronunciation, and variant-order",
            "  mismatches are zero.",
            "- Reproducibility: identical configuration produces",
            "  identical asset SHA256.",
            "- Storage: prefer 10% wheel or 20% installed reduction over the baseline.",
            "- RAM/runtime: report explicit RSS, cold-load, and lookup trade-offs.",
            "- Quality: every added lexicon shows measurable held-out marginal value.",
            "",
            "## 7. Licensing and production boundary",
            "",
            "Sources remain independent and are not merged into a",
            "redistributable asset.",
            "Resolve Crane CC-BY-SA-4.0 and gruut/eSpeak obligations before shipping.",
            "This report does not authorize modifying the production German pipeline.",
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
