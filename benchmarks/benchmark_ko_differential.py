#!/usr/bin/env python3
"""Compare the local Korean baseline with optional external frontends.

External packages are intentionally optional. Missing packages are reported as
unavailable rather than changing the runtime default or weakening the local
compatibility gate.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data" / "ko_differential.json"


def load_cases() -> dict[str, Any]:
    return json.loads(DATA.read_text(encoding="utf-8"))


def local_g2pkc(text: str) -> str:
    from kokorog2p.ko import KoreanG2P

    return KoreanG2P(morphology="off", output="jamo", to_syl=True).phonemize(text)


def optional_backend_status() -> dict[str, str]:
    candidates = {
        "upstream-g2pK": "g2pk",
        "KSS": "kss",
        "Pecab": "pecab",
        "ko-speech-tools": "ko_speech_tools",
        "mecab-ko": "mecab_ko",
    }
    status = {}
    for label, module_name in candidates.items():
        try:
            importlib.import_module(module_name)
        except ImportError:
            status[label] = "unavailable"
        else:
            status[label] = "installed, adapter review required"
    return status


def compare_local(cases: list[dict[str, Any]]) -> dict[str, Any]:
    matches = 0
    by_category: dict[str, list[bool]] = {}
    for case in cases:
        matched = local_g2pkc(case["source"]) == case["expected_jamo"]
        matches += matched
        by_category.setdefault(case["category"], []).append(matched)
    return {
        "backend": "local-g2pkc",
        "matches": matches,
        "total": len(cases),
        "exact_match_percent": matches / len(cases) * 100 if cases else 0,
        "categories": {
            category: sum(values) / len(values) * 100
            for category, values in by_category.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", action="store_true", help="Print machine-readable output"
    )
    args = parser.parse_args()

    data = load_cases()
    result = {
        "schema_version": data["schema_version"],
        "baseline": "5Hyeons/StyleTTS2 vocos g2pkc",
        "local": compare_local(data["cases"]),
        "optional_backends": optional_backend_status(),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Local g2pkc exact match: {result['local']['exact_match_percent']:.1f}%")
        for name, status in result["optional_backends"].items():
            print(f"{name}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
