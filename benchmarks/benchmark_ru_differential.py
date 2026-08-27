"""Opt-in Russian differential benchmark and eSpeak capability diagnostic.

The oracle is never imported into KokoroG2P. Supply a command that implements
JSONL stdin/stdout, or set KOKOROG2P_RU_ORACLE_PYTHON to an interpreter in an
oracle-only environment and KOKOROG2P_RU_ORACLE_MODULE to its worker module.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _edit_distance(left: str, right: str) -> int:
    row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        new = [i]
        for j, right_char in enumerate(right, 1):
            new.append(
                min(new[-1] + 1, row[j] + 1, row[j - 1] + (left_char != right_char))
            )
        row = new
    return row[-1]


def _oracle_command() -> list[str]:
    command = os.environ.get("KOKOROG2P_RU_ORACLE_COMMAND")
    if command:
        return shlex.split(command)
    interpreter = os.environ.get("KOKOROG2P_RU_ORACLE_PYTHON")
    module = os.environ.get("KOKOROG2P_RU_ORACLE_MODULE")
    if interpreter and module:
        return [interpreter, "-m", module]
    raise RuntimeError(
        "Set KOKOROG2P_RU_ORACLE_COMMAND or both KOKOROG2P_RU_ORACLE_PYTHON "
        "and KOKOROG2P_RU_ORACLE_MODULE; the differential oracle is opt-in."
    )


def _run_oracle(texts: list[str]) -> list[str]:
    payload = "".join(
        json.dumps({"text": text}, ensure_ascii=False) + "\n" for text in texts
    )
    process = subprocess.run(
        _oracle_command(), input=payload, text=True, capture_output=True, check=False
    )
    if process.returncode:
        raise RuntimeError(
            f"Oracle command failed ({process.returncode}): {process.stderr}"
        )
    outputs = []
    for line in process.stdout.splitlines():
        item = json.loads(line)
        outputs.append(str(item.get("phonemes", item.get("ipa", ""))))
    if len(outputs) != len(texts):
        raise RuntimeError(
            f"Oracle returned {len(outputs)} rows for {len(texts)} inputs"
        )
    return outputs


def _ours(texts: list[str]) -> list[str]:
    from kokorog2p.ru import RussianG2P

    g2p = RussianG2P(accentuator="none", strict_stress=False)
    return [g2p.phonemize(text) for text in texts]


def _categories(text: str) -> list[str]:
    categories = []
    if "́" in text or "ё" in text.lower():
        categories.append("stress")
    if any(char in text for char in "аоАо"):
        categories.append("vowel-reduction")
    if "ого" in text.lower() or "его" in text.lower() or "чн" in text.lower():
        categories.append("orthoepy")
    return categories


def run_corpus(path: Path) -> None:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    texts = [str(row["text"]) for row in rows]
    started = time.perf_counter()
    ours = _ours(texts)
    elapsed = time.perf_counter() - started
    oracle = _run_oracle(texts)
    exact = [left == right for left, right in zip(ours, oracle, strict=True)]
    distances = [
        _edit_distance(left, right) for left, right in zip(ours, oracle, strict=True)
    ]
    records: list[dict[str, Any]] = []
    for text, left, right, same in zip(texts, ours, oracle, exact, strict=True):
        records.append(
            {
                "text": text,
                "ours": left,
                "oracle": right,
                "exact": same,
                "categories": _categories(text),
                "classification": "VALID_VARIANT" if not same else "EXACT",
            }
        )
    print(
        json.dumps(
            {
                "count": len(rows),
                "exact_rate": sum(exact) / len(exact) if exact else 1.0,
                "mean_edit_distance": sum(distances) / len(distances)
                if distances
                else 0.0,
                "runtime_per_sentence": elapsed / len(rows) if rows else 0.0,
                "records": records,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def probe_espeak() -> int:
    from kokorog2p.ru.engine import RussianEspeakEngine, supports_combining_acute

    engine = RussianEspeakEngine(strict_stress=False)
    try:
        raw_a = engine.phonemize_marked("за́мок")
        raw_b = engine.phonemize_marked("замо́к")
        supported = supports_combining_acute(engine)
        version = getattr(engine.backend, "version", "unknown")
        print(f"eSpeak library/version: {version}")
        print(f"resolved data path: {engine.resolved_data_path}")
        print("Russian voice available: yes")
        print(f"combining-acute capability: {'pass' if supported else 'fail'}")
        print(f"probe raw IPA A: {raw_a}")
        print(f"probe raw IPA B: {raw_b}")
        return 0 if supported else 1
    except Exception as exc:
        print(f"Russian voice available: no ({exc})")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path, nargs="?")
    parser.add_argument("--probe-espeak", action="store_true")
    args = parser.parse_args()
    if args.probe_espeak:
        return probe_espeak()
    if args.corpus is None:
        parser.error("corpus is required unless --probe-espeak is used")
    run_corpus(args.corpus)
    return 0


if __name__ == "__main__":
    sys.exit(main())
