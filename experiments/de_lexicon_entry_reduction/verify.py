"""Independent exact verification for a reloaded candidate."""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections.abc import Iterable
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from typing import Any

from experiments.de_lexicon_compression.lexlab.sources import load_source

try:
    from .lexreduce.audit import audit_runtime_representation
    from .lexreduce.serializer import load_asset
except ImportError:  # direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from experiments.de_lexicon_entry_reduction.lexreduce.audit import (
        audit_runtime_representation,
    )
    from experiments.de_lexicon_entry_reduction.lexreduce.serializer import load_asset


def adversarial_misses(words: Iterable[str], *, limit: int = 256) -> tuple[str, ...]:
    """Create deterministic miss variants without returning known words."""

    known = set(words)
    candidates: list[str] = []
    ordered = sorted(known)
    for word in ordered:
        if len(word) > 1:
            candidates.append(word[:-1])
        candidates.append(word + "x")
        candidates.append(word.swapcase())
        candidates.append(word + "\u0301")
        if len(word) > 1:
            candidates.append(word[1:] + word[:1])
        if len(candidates) >= limit * 4:
            break
    unique = sorted(set(candidates) - known)
    randomizer = random.Random(0)
    randomizer.shuffle(unique)
    return tuple(sorted(unique[:limit]))


def verify_candidate(
    candidate: Any,
    baseline: Any,
    *,
    miss_words: Iterable[str] | None = None,
) -> dict[str, Any]:
    words = tuple(baseline.words)
    missing = 0
    pronunciation_mismatches = 0
    variant_count_mismatches = 0
    variant_order_mismatches = 0
    invariant_failures = 0
    for word in words:
        if not candidate.is_known(word):
            missing += 1
            continue
        expected = baseline.lookup_all(word)
        try:
            actual = candidate.lookup_all(word)
        except (IndexError, KeyError, RuntimeError):
            invariant_failures += 1
            continue
        if len(actual) != len(expected):
            variant_count_mismatches += 1
        elif actual != expected:
            variant_order_mismatches += 1
        if actual != expected:
            pronunciation_mismatches += 1

    misses = tuple(miss_words or adversarial_misses(words))
    false_positives = sum(candidate.is_known(word) for word in misses)
    audit = audit_runtime_representation(candidate)
    return {
        "words_checked": len(words),
        "variants_checked": sum(len(baseline.lookup_all(word)) for word in words),
        "missing_words": missing,
        "extra_words": false_positives,
        "pronunciation_mismatches": pronunciation_mismatches,
        "variant_count_mismatches": variant_count_mismatches,
        "variant_order_mismatches": variant_order_mismatches,
        "membership_false_negatives": missing,
        "membership_false_positives": false_positives,
        "invariant_failures": invariant_failures,
        "lossless": not any(
            (
                missing,
                false_positives,
                pronunciation_mismatches,
                variant_count_mismatches,
                variant_order_mismatches,
                invariant_failures,
            )
        ),
        "audit": audit,
        "miss_words_checked": len(misses),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        required=True,
        help="run directory containing candidate.asset",
    )
    parser.add_argument("--source", default="builtin")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--path", type=Path)
    args = parser.parse_args()
    baseline = load_source(
        args.source, data_root=args.data_root, path=args.path
    ).runtime_unique()
    candidate = load_asset(args.run / "candidate.asset")
    result = verify_candidate(candidate, baseline)
    (args.run / "verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    (args.run / "independent-verification.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0 if result["lossless"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
