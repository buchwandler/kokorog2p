"""Czech prepared-text typography regressions."""

from kokorog2p.cs.normalizer import CzechNormalizer


def test_czech_normalizer_preserves_semantic_preparation() -> None:
    for source in ("0", "Dr. Novák má 2 kg", "25°C"):
        assert CzechNormalizer()(source) == source


def test_czech_normalizer_has_no_structured_replacements() -> None:
    assert list(CzechNormalizer.iter_structured_replacements("2 kg a 2 kg")) == []


def test_czech_normalizer_protected_spans_are_untouched() -> None:
    source = "2 kg a 3 kg"
    assert CzechNormalizer()(source, protected_spans=((0, 4),)) == source


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
    assert CzechNormalizer().normalize_for_g2p("25°C – test") == "25°C — test"
