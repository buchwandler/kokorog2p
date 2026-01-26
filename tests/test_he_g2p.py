"""Tests for Hebrew G2P (Grapheme-to-Phoneme) conversion.

These tests verify the Hebrew G2P functionality using the phonikud package.
Note: phonikud package may not be installed by default, so tests will be skipped
if it's not available.
"""

import pytest

from kokorog2p import get_g2p, phonemize


class TestHebrewG2P:
    """Test Hebrew G2P class."""

    def test_creation(self):
        """Test that Hebrew G2P can be created."""
        g2p = get_g2p("he")
        assert g2p is not None
        assert g2p.language == "he"

    def test_call_returns_tokens(self):
        """Test that calling g2p returns a list of tokens."""
        g2p = get_g2p("he")
        text = "שלום"  # shalom
        tokens = g2p(text)
        assert isinstance(tokens, list)
        assert len(tokens) > 0
        assert all(hasattr(t, "text") for t in tokens)
        assert all(hasattr(t, "phonemes") for t in tokens)

    def test_empty_input(self):
        """Test that empty input returns empty list."""
        g2p = get_g2p("he")
        assert g2p("") == []
        assert g2p("   ") == []

    def test_phonemize_method(self):
        """Test the phonemize convenience function."""
        text = "שלום"  # shalom
        result = phonemize(text, language="he")
        assert isinstance(result.phonemes, str)

    def test_repr(self):
        """Test string representation."""
        g2p = get_g2p("he")
        repr_str = repr(g2p)
        assert "HebrewG2P" in repr_str
        assert "language='he'" in repr_str

    def test_basic_hebrew_with_nikud(self):
        """Test Hebrew text with nikud (diacritics)."""
        pytest.importorskip("phonikud")
        g2p = get_g2p("he")
        # "shalom" with nikud
        text = "שָׁלוֹם"
        tokens = g2p(text)
        assert len(tokens) > 0
        # Should have phonemes if phonikud is available
        if tokens[0].phonemes:
            assert isinstance(tokens[0].phonemes, str)
            assert len(tokens[0].phonemes) > 0

    def test_greeting(self):
        """Test Hebrew greeting."""
        pytest.importorskip("phonikud")
        g2p = get_g2p("he")
        text = "שָׁלוֹם עוֹלָם"  # shalom olam (hello world)
        tokens = g2p(text)
        assert len(tokens) > 0

    def test_without_nikud(self):
        """Test Hebrew text without nikud."""
        g2p = get_g2p("he")
        text = "שלום"  # shalom without nikud
        tokens = g2p(text)
        assert len(tokens) > 0
        # May or may not have phonemes depending on phonikud's capabilities

    def test_preserve_punctuation_option(self):
        """Test preserve_punctuation option."""
        from kokorog2p.he import HebrewG2P

        g2p_with_punct = HebrewG2P(preserve_punctuation=True)
        g2p_without_punct = HebrewG2P(preserve_punctuation=False)

        assert g2p_with_punct.preserve_punctuation is True
        assert g2p_without_punct.preserve_punctuation is False

    def test_preserve_stress_option(self):
        """Test preserve_stress option."""
        from kokorog2p.he import HebrewG2P

        g2p_with_stress = HebrewG2P(preserve_stress=True)
        g2p_without_stress = HebrewG2P(preserve_stress=False)

        assert g2p_with_stress.preserve_stress is True
        assert g2p_without_stress.preserve_stress is False

    def test_load_parameters(self):
        """Test that load_gold and load_silver parameters are accepted."""
        g2p = get_g2p("he", load_gold=True, load_silver=True)
        assert g2p.load_gold is True
        assert g2p.load_silver is True

    def test_lookup_method(self):
        """Test the lookup method."""
        g2p = get_g2p("he")
        result = g2p.lookup("שלום")
        # Result may be None if phonikud is not available
        assert result is None or isinstance(result, str)


class TestHebrewG2PIntegration:
    """Test Hebrew G2P integration with main API."""

    def test_get_g2p_hebrew(self):
        """Test getting Hebrew G2P from main API."""
        g2p = get_g2p("he")
        assert g2p is not None
        assert g2p.language == "he"

    def test_get_g2p_hebrew_variants(self):
        """Test different Hebrew language codes."""
        codes = ["he", "he-il", "heb", "hebrew"]
        for code in codes:
            g2p = get_g2p(code)
            assert g2p is not None
            # Language code gets normalized
            assert g2p.language in ["he", "he-il", "heb", "hebrew"]

    def test_phonemize_hebrew(self):
        """Test phonemize function with Hebrew."""
        text = "שלום"
        result = phonemize(text, language="he")
        assert isinstance(result.phonemes, str)

    def test_extra_kwargs_passed_to_phonikud(self):
        """Test that extra kwargs are passed to phonikud."""
        # This just tests that extra kwargs don't cause errors
        g2p = get_g2p("he", some_extra_param=True)
        assert g2p is not None
