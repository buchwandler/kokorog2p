"""Test for temperature normalization bug fix (issue with C. → circa)."""

import pytest

from kokorog2p import clear_cache, get_g2p


class TestTemperatureNormalization:
    """Test that temperature patterns are normalized before abbreviation expansion."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_celsius_with_period(self):
        """Test that 37°C. is expanded to Celsius, not circa."""
        g2p = get_g2p("en-us")

        text = "The temperature is 37°C."
        result = g2p.phonemize(text)

        # Should contain "Celsius" phonemes, not "circa"
        assert "sˈɛlsiəs." in result or "sɛlsiəs." in result
        # Should NOT contain "circa" phonemes
        assert "sˈɜɹkə" not in result and "sɜɹkə" not in result

    def test_fahrenheit_with_period(self):
        """Test that 98°F. is expanded to Fahrenheit, not to f."""
        g2p = get_g2p("en-us")

        text = "Body temp is 98°F."
        result = g2p.phonemize(text)

        # Should contain "Fahrenheit" phonemes
        assert (
            "fˈɛɹənhˌIt." in result or "fɛɹənhˌIt." in result or "fˈɛɹənhIt." in result
        )

    def test_celsius_without_period(self):
        """Test that 37°C (no period) still works."""
        g2p = get_g2p("en-us")

        text = "approximately 37°C"
        result = g2p.phonemize(text)

        # Should contain "Celsius" phonemes
        assert "sˈɛlsiəs" in result or "sɛlsiəs" in result

    def test_celsius_mid_sentence(self):
        """Test that 37°C in middle of sentence works."""
        g2p = get_g2p("en-us")

        text = "It is 37°C outside today."
        result = g2p.phonemize(text)

        # Should contain "Celsius" phonemes
        assert "sˈɛlsiəs" in result or "sɛlsiəs" in result

    def test_negative_celsius(self):
        """Test negative temperatures."""
        g2p = get_g2p("en-us")

        text = "It's -40°C."
        result = g2p.phonemize(text)

        # Should contain "Celsius" and "minus"
        assert "mˈInəs" in result or "mInəs" in result
        assert "sˈɛlsiəs." in result or "sɛlsiəs." in result

    def test_normalizer_directly(self):
        """Test the normalizer directly to verify order of operations."""
        from kokorog2p.en.normalizer import EnglishNormalizer

        normalizer = EnglishNormalizer(track_changes=True)
        text = "The temperature is 37°C."
        normalized, changes = normalizer.normalize(text)

        # Verify it normalized to Celsius, not circa
        assert "Celsius." in normalized
        assert "circa" not in normalized

        # Verify the temperature rule was applied
        rule_names = [change.rule_name for change in changes]
        assert "temperature_fahrenheit_celsius" in rule_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
