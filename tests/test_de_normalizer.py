"""Tests for German typography in the prepared-text core."""

import pytest

from kokorog2p.de.normalizer import GermanNormalizer


@pytest.fixture
def normalizer() -> GermanNormalizer:
    return GermanNormalizer()


def test_prepared_semantic_forms_are_preserved(normalizer: GermanNormalizer) -> None:
    for text in ("1 kg", "15.01.2026", "14:05", "12,50 EUR", "Dr. Smith"):
        assert normalizer(text) == text


def test_intrinsic_normalization_is_available(normalizer: GermanNormalizer) -> None:
    assert normalizer.normalize_for_g2p("Hallo - Welt") == "Hallo - Welt"


def test_invalid_structured_forms_are_preserved(normalizer: GermanNormalizer) -> None:
    assert normalizer("32.13.2026") == "32.13.2026"
    assert normalizer("25:99") == "25:99"


def test_repeated_normalization_is_idempotent(normalizer: GermanNormalizer) -> None:
    text = "Hallo – Welt"
    assert normalizer(normalizer(text)) == normalizer(text)


def test_tracking_has_no_semantic_replacements() -> None:
    normalizer = GermanNormalizer(track_changes=True)
    normalized, changes = normalizer.normalize("2 kg")
    assert normalized == "2 kg"
    assert not changes
