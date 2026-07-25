#!/usr/bin/env python3
"""Rebuild lexicon entries using espeak-based phonemizers."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RebuildStats:
    total: int = 0
    updated: int = 0
    failed: int = 0


def _regenerate_value(
    word: str,
    value: str,
    phonemize_fn: Callable[[str], str | None],
    failures: set[str],
) -> str:
    phonemes = phonemize_fn(word)
    if phonemes:
        return phonemes
    failures.add(word)
    return value


def _regenerate_special_case(
    word: str,
    value: dict[str, object],
    phonemize_fn: Callable[[str], str | None],
    failures: set[str],
) -> dict[str, object]:
    rebuilt: dict[str, object] = {}
    for key, entry in value.items():
        if key == "DEFAULT" and isinstance(entry, str | type(None)):
            phonemes = phonemize_fn(word)
            if phonemes:
                rebuilt[key] = phonemes
            else:
                failures.add(word)
                rebuilt[key] = entry
        else:
            rebuilt[key] = entry
    return rebuilt


def rebuild_lexicon(
    entries: dict[str, object],
    phonemize_fn: Callable[[str], str | None],
) -> tuple[dict[str, object], RebuildStats, set[str]]:
    rebuilt: dict[str, object] = {}
    failures: set[str] = set()
    stats = RebuildStats()

    for word, value in entries.items():
        stats.total += 1
        if isinstance(value, str):
            new_value = _regenerate_value(word, value, phonemize_fn, failures)
        elif isinstance(value, dict):
            new_value = _regenerate_special_case(word, value, phonemize_fn, failures)
        else:
            raise TypeError(f"Unsupported lexicon entry for {word!r}: {type(value)}")

        if new_value != value:
            stats.updated += 1
        rebuilt[word] = new_value

    stats.failed = len(failures)
    return rebuilt, stats, failures


def rebuild_lexicon_file(
    input_path: Path,
    output_path: Path,
    phonemize_fn: Callable[[str], str | None],
) -> int:
    with input_path.open("r", encoding="utf-8") as handle:
        entries = json.load(handle)
    if not isinstance(entries, dict):
        raise TypeError(f"Expected dict in {input_path}")

    rebuilt, stats, failures = rebuild_lexicon(entries, phonemize_fn)

    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(rebuilt, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    print(f"Rebuilt {stats.total} entries")
    print(f"Updated {stats.updated} entries")
    if failures:
        print(f"Failed to regenerate {stats.failed} entries")
        print("First 10 failures:", ", ".join(sorted(failures)[:10]))
    print(f"Output: {output_path}")
    return 0
