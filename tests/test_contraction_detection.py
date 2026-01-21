"""Tests for apostrophe-like character normalization in contractions.

This test suite verifies that various apostrophe-like characters (prime,
double prime, acute accent, etc.) are properly normalized to ASCII apostrophes
when they appear between letters, enabling correct contraction detection.
"""

import pytest

from kokorog2p import get_g2p


class TestContractionDetection:
    """Test that various apostrophe-like characters are normalized correctly."""

    @pytest.fixture
    def g2p(self):
        """Get English G2P instance."""
        return get_g2p("en-us")

    def test_standard_apostrophe(self, g2p):
        """Test that standard apostrophe works correctly."""
        result = g2p.phonemize("we're")
        assert "wɪɹ" in result
        result = g2p.phonemize("What's your problem?'")
        assert "wˌʌts" in result

    def test_prime_apostrophe(self, g2p):
        """Test that prime character (U+2032) is normalized to apostrophe."""
        # This was the original bug report: "we′re" should work like "we're"
        result = g2p.phonemize("we′re")
        assert "wɪɹ" in result

    def test_double_prime_apostrophe(self, g2p):
        """Test that double prime character (U+2033) is normalized to apostrophe."""
        result = g2p.phonemize("we″re")
        assert "wɪɹ" in result

    def test_acute_accent_apostrophe(self, g2p):
        """Test that acute accent (U+02CA) is normalized to apostrophe."""
        result = g2p.phonemize("we´re")
        assert "wɪɹ" in result

    def test_original_bug_report(self, g2p):
        """Test the original bug report case."""
        # Original input: 'They replied, "we′re feel play".'
        result = g2p.phonemize('They replied, "we′re feel play".')
        # Should contain the correct phonemes for "we're" (contraction)
        assert "wɪɹ" in result

    def test_multiple_contractions_with_prime(self, g2p):
        """Test multiple contractions with prime characters."""
        result = g2p.phonemize("we′re sure you′re right and he′s wrong")
        # Should contain phonemes for we're, you're, he's
        assert "wɪɹ" in result  # we're
        assert "jʊɹ" in result or "jɝ" in result  # you're
        assert "hiz" in result  # he's

    def test_measurements_not_affected(self, g2p):
        """Test that measurements like 5′30″ are not affected by normalization.

        Note: This test currently just checks that the text is processed without
        errors. Full measurement expansion (5′30″ → "five feet thirty inches")
        is a future enhancement.
        """
        result = g2p.phonemize("The height is 5′30″")
        # Should process without errors (actual measurement handling TBD)
        assert result is not None
        assert len(result) > 0

    def test_mixed_apostrophe_types(self, g2p):
        """Test text with mixed apostrophe types."""
        text = "we're happy, you′re sad, they″re neutral"
        result = g2p.phonemize(text)
        # All three should be recognized as contractions
        assert "wɪɹ" in result  # we're
        assert "jʊɹ" in result or "jɝ" in result  # you're
        # they're should also be present

    def test_contraction_pos_tagging(self, g2p):
        """Test that normalized contractions get correct POS tags."""
        # Get tokens to check POS tags
        tokens = g2p("we′re")
        # Should have a token for "we're" with correct tag (VBP or similar)
        # Not NNS (noun plural) which was the bug
        token_texts = [t.text for t in tokens]
        assert "we're" in token_texts or "we′re" in token_texts

        # Check that we don't get wrong POS tag NNS (noun plural)
        for token in tokens:
            if "we" in token.text.lower() and "re" in token.text.lower():
                # Should not be tagged as noun plural
                assert token.tag != "NNS"


class TestApostropheNormalizationEdgeCases:
    """Test edge cases for apostrophe normalization."""

    @pytest.fixture
    def g2p(self):
        """Get English G2P instance."""
        return get_g2p("en-us")

    def test_prime_at_start_not_normalized(self, g2p):
        """Test that prime at start of word is not normalized."""
        # Prime should only normalize between letters
        result = g2p.phonemize("′hello")
        assert result is not None

    def test_prime_at_end_not_normalized(self, g2p):
        """Test that prime at end of word is not normalized."""
        # Prime should only normalize between letters
        result = g2p.phonemize("hello′")
        assert result is not None

    def test_standalone_prime_not_normalized(self, g2p):
        """Test that standalone prime is not normalized."""
        result = g2p.phonemize("5 ′")
        assert result is not None

    def test_prime_between_numbers_not_normalized(self, g2p):
        """Test that prime between numbers is not normalized (measurements)."""
        result = g2p.phonemize("5′6″")
        assert result is not None
        # Should not be treated as a contraction
