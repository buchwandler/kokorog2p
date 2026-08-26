#!/usr/bin/env python3
"""Create or compare Japanese frontend snapshots in clean environments.

Run this script once in an environment containing upstream pyopenjtalk and once
in an environment containing pyopenjtalk-plus. Never install both distributions
into the same environment because they provide the same import namespace.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from pathlib import Path
from typing import Any

DEFAULT_TEXTS = [
    "こんにちは、世界。",
    "今日はいい天気ですね。",
    "東京は日本の首都です。",
    "一人で三本のペンを買いました。",
    "コンピューターとヴァイオリン。",
]


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def create_snapshot(label: str, texts: list[str]) -> dict[str, Any]:
    """Capture frontend records and final model input for one clean environment."""
    from kokorog2p.ja import JapaneseG2P

    g2p = JapaneseG2P(backend="pyopenjtalk")
    rows = []
    for text in texts:
        rows.append(
            {
                "text": text,
                "frontend": g2p.pyopenjtalk.run_frontend(text),
                "model_input": g2p.phonemize(text),
            }
        )
    return {
        "label": label,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pyopenjtalk": package_version("pyopenjtalk"),
            "pyopenjtalk-plus": package_version("pyopenjtalk-plus"),
        },
        "rows": rows,
    }


def compare(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Classify differences at frontend and final model-input levels."""
    reference_rows = {row["text"]: row for row in reference["rows"]}
    differences = []
    for candidate_row in candidate["rows"]:
        text = candidate_row["text"]
        reference_row = reference_rows[text]
        frontend_changed = candidate_row["frontend"] != reference_row["frontend"]
        model_input_changed = (
            candidate_row["model_input"] != reference_row["model_input"]
        )
        if frontend_changed or model_input_changed:
            differences.append(
                {
                    "text": text,
                    "frontend_changed": frontend_changed,
                    "model_input_changed": model_input_changed,
                    "classification": (
                        "model_input_changed"
                        if model_input_changed
                        else "frontend_only"
                    ),
                }
            )
    return {
        "reference": reference["environment"],
        "candidate": candidate["environment"],
        "differences": differences,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", choices=["upstream", "plus"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--compare", nargs=2, metavar=("REFERENCE", "CANDIDATE"))
    parser.add_argument("--comparison-output", type=Path)
    args = parser.parse_args()

    if args.compare:
        reference = json.loads(Path(args.compare[0]).read_text(encoding="utf-8"))
        candidate = json.loads(Path(args.compare[1]).read_text(encoding="utf-8"))
        result = compare(reference, candidate)
        output = json.dumps(result, indent=2, ensure_ascii=False)
        if args.comparison_output:
            args.comparison_output.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
        return 0

    if not args.label or not args.output:
        parser.error("--label and --output are required when creating a snapshot")
    snapshot = create_snapshot(args.label, DEFAULT_TEXTS)
    args.output.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.label} snapshot to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
