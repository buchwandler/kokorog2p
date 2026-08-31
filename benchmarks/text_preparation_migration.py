"""Capture and compare the written-text preparation migration oracle.

The oracle is intentionally generated from the currently installed source tree.  It
records preparation and G2P observations without hard-coding phonemes produced by
optional backends, so a reviewed baseline can be regenerated on another machine.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests" / "data" / "text_preparation_migration.json"
DEFAULT_OUTPUT = ROOT / "tests" / "data" / "text_preparation_migration_baseline.jsonl"


def _package_version(name: str) -> str | None:
    try:
        return version(name)
    except Exception:
        return None


def _spokenform_language(language: str) -> str:
    """Resolve a Kokoro product alias before calling Spokenform."""
    from kokorog2p import _canonical_language

    return _canonical_language(language)


def _capture_case(case: dict[str, Any], *, capture_g2p: bool) -> dict[str, Any]:
    from spokenform import PreparationConfig, prepare_for_kokorog2p

    source_language = str(case["language"])
    language = _spokenform_language(source_language)
    source = str(case["source"])
    record: dict[str, Any] = {
        **case,
        "canonical_language": language,
        "spokenform_version": _package_version("spokenform"),
        "kokorog2p_version": _package_version("kokorog2p"),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    started = time.perf_counter()
    try:
        prepared = prepare_for_kokorog2p(
            source,
            language=language,
            config=PreparationConfig.for_kokorog2p(language),
        )
    except Exception as error:
        record["preparation_error"] = f"{type(error).__name__}: {error}"
        record["preparation_ms"] = round((time.perf_counter() - started) * 1000, 3)
        return record

    record.update(
        {
            "prepared_text": prepared.spoken_text,
            "source_replacements": [
                {
                    "source": item.source,
                    "replacement": item.replacement,
                    "source_start": item.source_start,
                    "source_end": item.source_end,
                    "rule": item.rule,
                    "kind": item.kind,
                    "language": item.language,
                }
                for item in prepared.source_replacements
            ],
            "warnings": list(prepared.warnings),
            "preparation_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    )
    if not capture_g2p:
        return record

    try:
        from kokorog2p.pipeline_api import phonemize_to_result

        g2p_started = time.perf_counter()
        result = phonemize_to_result(
            source,
            lang=source_language,
            return_ids=True,
            return_phonemes=True,
        )
        record.update(
            {
                "extended_text": result.extended_text,
                "phonemes": result.phonemes,
                "token_ids": result.token_ids,
                "g2p_warnings": result.warnings,
                "g2p_ms": round((time.perf_counter() - g2p_started) * 1000, 3),
                "backend": type(getattr(result, "g2p", None)).__name__
                if hasattr(result, "g2p")
                else None,
            }
        )
    except Exception as error:
        record["g2p_error"] = f"{type(error).__name__}: {error}"
    return record


def capture(*, output: Path, capture_g2p: bool) -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as stream:
        for case in cases:
            record = _capture_case(case, capture_g2p=capture_g2p)
            stream.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            for alias in case.get("aliases", []):
                alias_case = {**case, "id": f"{case['id']}@{alias}", "language": alias}
                record = _capture_case(alias_case, capture_g2p=capture_g2p)
                stream.write(
                    json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
                )


def benchmark(*, iterations: int) -> None:
    from spokenform import PreparationConfig, prepare_for_kokorog2p

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for case in cases:
        source = str(case["source"])
        language = str(case["language"])
        started = time.perf_counter()
        successes = 0
        for _ in range(iterations):
            try:
                prepare_for_kokorog2p(
                    source,
                    language=language,
                    config=PreparationConfig.for_kokorog2p(language),
                )
                successes += 1
            except Exception:
                pass
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "id": case["id"],
                "language": language,
                "iterations": iterations,
                "successes": successes,
                "total_ms": round(elapsed * 1000, 3),
                "average_ms": round(elapsed * 1000 / iterations, 3),
                "characters_per_second": round(len(source) * iterations / elapsed, 3)
                if elapsed
                else None,
            }
        )
    print(
        json.dumps({"python": sys.version, "rows": rows}, ensure_ascii=False, indent=2)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-g2p", action="store_true", help="capture preparation only"
    )
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()
    if args.benchmark:
        benchmark(iterations=args.iterations)
    else:
        capture(output=args.output, capture_g2p=not args.no_g2p)
        print(f"wrote migration baseline to {args.output}")


if __name__ == "__main__":
    main()
