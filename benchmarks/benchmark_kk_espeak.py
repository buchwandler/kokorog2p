"""Diagnostic benchmark for the Kazakh eSpeak-NG frontend."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SAMPLES = [
    "Әә Ғғ Ққ Ңң Өө Ұұ Үү Һһ Іі",
    "әке ғалым қазақ таң өлең құс үкі",
    "Сәлем әлем.",
    "Қазақстан Республикасы.",
    "Бұл қазақ тіліндегі сөйлеу синтезі.",
    "Менде 42 кітап бар.",
    "2026 жылы 3.14 мысал.",
    "Кокоро және eSpeak-NG.",
    "Сәлем, world!",
]


def _symbols(text: str) -> list[str]:
    return sorted(set(text.replace(" ", "")))


def _run(*, use_cli: bool, epitran: bool) -> dict[str, Any]:
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.kk.model_profile import (
        _ESPEAK_TIED_MAP,
        transform_kazakh_ipa,
        validate_kazakh_symbols,
    )

    backend = EspeakBackend(language="kk", use_cli=use_cli)
    records: list[dict[str, Any]] = []
    raw_symbols: set[str] = set()
    normalized_symbols: set[str] = set()
    invalid_symbols: Counter[str] = Counter()
    invalid_words: list[str] = []
    rule_hits: Counter[str] = Counter()
    epitran_engine: Any | None = None

    if epitran:
        try:
            from epitran import Epitran

            epitran_engine = Epitran("kaz-Cyrl")
        except ImportError:
            print(
                "Epitran not installed; continuing without differential output.",
                file=sys.stderr,
            )

    for text in SAMPLES:
        raw = backend.phonemize(text, convert_to_kokoro=False)
        normalized = transform_kazakh_ipa(raw)
        invalid = validate_kazakh_symbols(normalized, strict=False)
        raw_symbols.update(_symbols(raw))
        normalized_symbols.update(_symbols(normalized))
        invalid_symbols.update(invalid)
        if invalid:
            invalid_words.append(text)
        for old in _ESPEAK_TIED_MAP:
            count = raw.count(old)
            if count:
                rule_hits[old] += count

        record: dict[str, Any] = {
            "text": text,
            "raw_espeak": raw,
            "normalized": normalized,
            "invalid_symbols": invalid,
            "valid_for_model": not invalid,
        }
        if epitran_engine is not None:
            record["epitran"] = epitran_engine.transliterate(text)
        records.append(record)

    return {
        "summary": {
            "total_samples": len(records),
            "empty_espeak_outputs": sum(not item["raw_espeak"] for item in records),
            "unique_raw_ipa_symbols": sorted(raw_symbols),
            "unique_normalized_symbols": sorted(normalized_symbols),
            "unsupported_kokoro_symbols": sorted(invalid_symbols),
            "words_with_unsupported_symbols": invalid_words,
            "transform_rule_hit_counts": dict(rule_hits),
            "espeak_version": backend.version,
            "espeak_voice": backend.language,
            "backend": "cli" if use_cli else "library",
        },
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json", type=Path, metavar="PATH", help="write the report as JSON"
    )
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument(
        "--strict", action="store_true", help="exit non-zero for invalid output"
    )
    parser.add_argument(
        "--epitran", action="store_true", help="add optional Epitran diagnostics"
    )
    parser.add_argument(
        "--use-cli", action="store_true", help="use the eSpeak CLI backend"
    )
    args = parser.parse_args()

    try:
        report = _run(use_cli=args.use_cli, epitran=args.epitran)
    except Exception as error:
        print(f"Kazakh eSpeak-NG benchmark failed: {error}", file=sys.stderr)
        return 1

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        args.json.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if args.show_failures:
        for record in report["records"]:
            if not record["valid_for_model"]:
                print(
                    f"FAIL {record['text']!r}: {record['invalid_symbols']}",
                    file=sys.stderr,
                )
    return int(args.strict and bool(report["summary"]["unsupported_kokoro_symbols"]))


if __name__ == "__main__":
    raise SystemExit(main())
