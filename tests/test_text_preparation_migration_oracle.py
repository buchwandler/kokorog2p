"""Structural checks for the cross-repository text-preparation migration oracle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"
CASES = json.loads((DATA / "text_preparation_migration.json").read_text(encoding="utf-8"))
BASELINE = DATA / "text_preparation_migration_baseline.jsonl"
EXPECTED_LANGUAGES = {
    "en",
    "de",
    "fr",
    "es",
    "it",
    "pt",
    "cs",
    "vi",
    "ko",
    "he",
    "zh",
    "ja",
    "ar",
    "sv",
    "th",
    "ru",
    "kk",
}


def test_oracle_covers_all_kokoro_language_families() -> None:
    assert {case["language"].split("-", 1)[0] for case in CASES} == EXPECTED_LANGUAGES
    assert all(case["id"] and case["source"] and case["language"] for case in CASES)


def test_oracle_has_reviewed_baseline_records() -> None:
    if not BASELINE.exists():
        pytest.fail(
            "baseline missing; run python benchmarks/text_preparation_migration.py "
            "before changing semantic preparation"
        )

    records = [json.loads(line) for line in BASELINE.read_text(encoding="utf-8").splitlines()]
    assert records
    assert {record["canonical_language"].split("-", 1)[0] for record in records} >= EXPECTED_LANGUAGES
    assert all(record.get("spokenform_version") for record in records)
    assert all("source" in record and "language" in record for record in records)
    assert all("preparation_ms" in record for record in records)


def test_oracle_records_source_replacement_coordinates() -> None:
    records = [json.loads(line) for line in BASELINE.read_text(encoding="utf-8").splitlines()]
    for record in records:
        for replacement in record.get("source_replacements", []):
            start = replacement["source_start"]
            end = replacement["source_end"]
            assert record["source"][start:end] == replacement["source"]
            assert 0 <= start <= end <= len(record["source"])


def test_aliases_are_present_in_the_oracle() -> None:
    assert any("aliases" in case and case["aliases"] for case in CASES)
    records = [json.loads(line) for line in BASELINE.read_text(encoding="utf-8").splitlines()]
    assert any("@" in record["id"] for record in records)
