"""Prepared-text temperature handling regressions."""

from kokorog2p import clear_cache, get_g2p
from kokorog2p.en.normalizer import EnglishNormalizer


def setup_function() -> None:
    clear_cache()


def test_celsius_symbols_are_consumed_as_prepared_text() -> None:
    result = get_g2p("en-us").phonemize("The temperature is 37°C.")
    assert result
    assert "sˈɜɹkə" not in result and "sɜɹkə" not in result


def test_fahrenheit_symbols_are_not_semantically_expanded() -> None:
    result = get_g2p("en-us").phonemize("Body temp is 98°F.")
    assert result
    assert "fˈɛɹənh" not in result


def test_negative_temperature_keeps_numeric_source() -> None:
    result = get_g2p("en-us").phonemize("It's -40°C.")
    assert result
    assert "sˈɛlsiəs" not in result and "sɛlsiəs" not in result


def test_normalizer_does_not_interpret_temperature_semantics() -> None:
    normalizer = EnglishNormalizer(track_changes=True)
    source = "The temperature is 37°C."
    normalized, changes = normalizer.normalize(source)
    assert normalized == source
    assert not changes
