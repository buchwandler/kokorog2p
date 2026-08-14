"""Czech spokenform adapter and typography regressions."""

import json
from pathlib import Path

from kokorog2p.cs.normalizer import CzechNormalizer

PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "cs_spokenform_parity.json").read_text(
        encoding="utf-8"
    )
)


def test_czech_normalizer_matches_spokenform_parity_cases() -> None:
    for case in PARITY_CASES:
        assert CzechNormalizer()(case["source"]) == case["expected"], case["id"]


def test_czech_normalizer_tracks_source_aligned_semantics() -> None:
    normalizer = CzechNormalizer(track_changes=True)
    source = "Dr. Novák má 2 kg a teplota je 25°C."

    normalized, steps = normalizer.normalize(source)

    assert normalized == (
        "Doktor Novák má dva kilogramy a teplota je dvacet pět stupňů Celsia."
    )
    assert [(step.position, step.original, step.normalized) for step in steps[:3]] == [
        (0, "Dr.", "Doktor"),
        (13, "2 kg", "dva kilogramy"),
        (31, "25°C", "dvacet pět stupňů Celsia"),
    ]


def test_czech_normalizer_preserves_repeated_source_positions() -> None:
    source = "2 kg a 2 kg"
    replacements = list(CzechNormalizer.iter_structured_replacements(source))

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (0, 4, "dva kilogramy"),
        (7, 11, "dva kilogramy"),
    ]


def test_czech_normalizer_protected_spans_are_untouched() -> None:
    source = "2 kg a 3 kg"
    assert CzechNormalizer()(source, protected_spans=((0, 4),)) == (
        "2 kg a tři kilogramy"
    )


def test_czech_token_normalization_is_typography_only() -> None:
    normalizer = CzechNormalizer()

    assert normalizer.normalize_token("2") == "2"
    assert normalizer.normalize_token("Dr.") == "Dr."
    assert normalizer.normalize_token("\u2019") == "'"
    assert normalizer.normalize_token("2", apply_rules=False) == "2"


def test_czech_typography_composition_is_preserved() -> None:
    assert CzechNormalizer()("„...“ «...» ‘...’ ’...’ … – —") == (
        "\"...\" “...” '...' '...' … — —"
    )


def test_czech_normalize_for_g2p_only_applies_typography() -> None:
    normalizer = CzechNormalizer()

    assert normalizer.normalize_for_g2p("25°C – test") == "25°C — test"
