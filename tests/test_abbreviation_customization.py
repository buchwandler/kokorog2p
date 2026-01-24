"""Tests for abbreviation customization functionality."""

import pytest

from kokorog2p import clear_cache, get_g2p, reset_abbreviations
from kokorog2p.en import EnglishG2P
from kokorog2p.en.abbreviations import get_expander


class TestAbbreviationCustomization:
    """Test abbreviation add/remove functionality."""

    def setup_method(self):
        """Clear cache and reset abbreviations before each test."""
        reset_abbreviations()
        clear_cache()

    def test_remove_abbreviation(self):
        """Test removing an existing abbreviation."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        # Verify Dr. exists initially
        assert g2p.has_abbreviation("Dr.")

        # Remove it
        result = g2p.remove_abbreviation("Dr.")
        assert result is True

        # Verify it's gone
        assert not g2p.has_abbreviation("Dr.")

        # Test phonemization - should not expand
        text = "Dr. Smith lives here."
        result_text = g2p.phonemize(text)
        # "Dr." should remain unexpanded (will be treated as unknown or literal)
        assert "dˈɑktɜ" not in result_text  # "Doctor" should not appear

    def test_add_simple_abbreviation(self):
        """Test adding a simple abbreviation."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        # Add custom abbreviation
        g2p.add_abbreviation("Tech.", "Technology")

        # Verify it exists
        assert g2p.has_abbreviation("Tech.")

        # Test phonemization
        text = "Tech. is advancing rapidly."
        result = g2p.phonemize(text)
        # Should expand to "Technology"
        assert "tˈɛk" in result or "tɛk" in result  # Part of "Technology"

    def test_replace_abbreviation(self):
        """Test replacing Dr. with Drive expansion."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        # Remove old Dr. abbreviation
        g2p.remove_abbreviation("Dr.")

        # Add new one with only Drive expansion
        g2p.add_abbreviation("Dr.", "Drive")

        # Test phonemization
        text = "I live on Main Dr."
        result = g2p.phonemize(text)
        # Should expand to "Drive" - check for "drive" phonemes
        # The result contains it as dɹˈIv (with capital I for /aɪ/)
        assert "dɹ" in result and ("Iv" in result or "aɪv" in result or "Av" in result)

    def test_context_aware_abbreviation(self):
        """Test adding context-aware abbreviation."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        # Add context-aware abbreviation (overwrite St.)
        g2p.add_abbreviation(
            "St.",
            {"default": "Street", "place": "Street", "religious": "Saint"},
            "Street or Saint",
        )

        # Test place context (address)
        text1 = "123 Main St."
        result1 = g2p.phonemize(text1)
        # Should expand to "Street"
        assert "stɹ" in result1  # Part of "Street"

        # Test religious context
        text2 = "St. Peter"
        result2 = g2p.phonemize(text2)
        # May expand to either depending on context detection
        # Just verify it expands to something
        assert len(result2) > 10  # Should be phonemized

    def test_list_abbreviations(self):
        """Test listing all abbreviations."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        abbrevs = g2p.list_abbreviations()

        # Should be a list
        assert isinstance(abbrevs, list)

        # Should contain common abbreviations
        assert "Dr." in abbrevs
        assert "Mr." in abbrevs
        assert "Mrs." in abbrevs

    def test_persistence_across_instances(self):
        """Test that changes persist across get_g2p calls (singleton behavior)."""
        # First instance
        g2p1 = get_g2p("en-us")
        assert isinstance(g2p1, EnglishG2P)
        g2p1.add_abbreviation("Custom.", "Customized")

        # Second instance (from cache)
        g2p2 = get_g2p("en-us")
        assert isinstance(g2p2, EnglishG2P)

        # Should have the custom abbreviation
        assert g2p2.has_abbreviation("Custom.")

        # Clean up
        g2p2.remove_abbreviation("Custom.")

    def test_remove_nonexistent_abbreviation(self):
        """Test removing an abbreviation that doesn't exist."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        result = g2p.remove_abbreviation("NonExistent.")
        assert result is False

    def test_reset_abbreviations(self):
        """Custom abbreviations should clear after reset."""
        g2p = get_g2p("en-us", use_spacy=False)
        g2p.add_abbreviation("Custom.", "Customized")
        assert g2p.has_abbreviation("Custom.")

        clear_cache()
        g2p_cached = get_g2p("en-us", use_spacy=False)
        assert g2p_cached.has_abbreviation("Custom.")

        reset_abbreviations()
        g2p_reset = get_g2p("en-us", use_spacy=False)
        assert not g2p_reset.has_abbreviation("Custom.")

    def test_case_sensitivity(self):
        """Test case-sensitive abbreviation handling."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        # Most abbreviations are case-insensitive by default
        assert g2p.has_abbreviation("dr.")  # lowercase
        assert g2p.has_abbreviation("Dr.")  # capitalized

        # Add case-sensitive abbreviation
        g2p.add_abbreviation("ABC", "Always Be Coding", case_sensitive=True)

        assert g2p.has_abbreviation("ABC", case_sensitive=True)
        # Should not match lowercase
        assert not g2p.has_abbreviation("abc", case_sensitive=True)

        # Clean up
        g2p.remove_abbreviation("ABC", case_sensitive=True)

    def test_invalid_context(self):
        """Test that invalid context raises error."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        with pytest.raises(ValueError, match="Unknown context"):
            g2p.add_abbreviation("Test.", {"invalid_context": "Test"})

    def test_dict_expansion_with_default(self):
        """Test dict expansion uses explicit default."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        g2p.add_abbreviation("Ex.", {"default": "Example", "place": "Exit"})

        # In neutral context, should use default
        text = "Ex. shows this."
        result = g2p.phonemize(text)
        # Just check it got phonemized
        assert "ɛ" in result or "ɪ" in result  # Example phonemes

        # Clean up
        g2p.remove_abbreviation("Ex.")

    def test_dict_expansion_without_default(self):
        """Test dict expansion without explicit default uses first value."""
        g2p = get_g2p("en-us")
        assert isinstance(g2p, EnglishG2P)

        g2p.add_abbreviation("Tst.", {"place": "Test"})

        # Should use the first (and only) expansion
        assert g2p.has_abbreviation("Tst.")

        # Clean up
        g2p.remove_abbreviation("Tst.")


class TestNormalizerAbbreviationMethods:
    """Test abbreviation methods on EnglishNormalizer directly."""

    def test_normalizer_without_abbreviations_enabled(self):
        """Test that methods raise error when abbreviations disabled."""
        from kokorog2p.en.normalizer import EnglishNormalizer

        normalizer = EnglishNormalizer(expand_abbreviations=False)

        with pytest.raises(RuntimeError, match="expand_abbreviations is disabled"):
            normalizer.add_abbreviation("Test.", "Test")

        with pytest.raises(RuntimeError, match="expand_abbreviations is disabled"):
            normalizer.remove_abbreviation("Dr.")

        # has_abbreviation and list should not raise, just return empty
        assert normalizer.has_abbreviation("Dr.") is False
        assert normalizer.list_abbreviations() == []


class TestExpanderMethods:
    """Test the base expander methods."""

    def test_expander_get_abbreviation(self):
        """Test getting abbreviation entry."""
        reset_abbreviations()
        expander = get_expander()

        entry = expander.get_abbreviation("Mr.")  # Use Mr. which is stable
        assert entry is not None
        assert entry.abbreviation == "Mr."
        assert "Mister" in entry.expansion

    def test_expander_nonexistent_abbreviation(self):
        """Test getting nonexistent abbreviation."""
        reset_abbreviations()
        expander = get_expander()

        entry = expander.get_abbreviation("NonExistent.")
        assert entry is None

    def test_expander_context_warning(self):
        """Warn when expander settings change after init."""
        reset_abbreviations()
        get_expander(enable_context_detection=True)
        with pytest.warns(RuntimeWarning, match="enable_context_detection"):
            get_expander(enable_context_detection=False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
