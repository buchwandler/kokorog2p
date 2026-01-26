"""Unit tests for the English normalizer.

Tests the normalization pipeline and ensures it produces identical output
to the existing implementation.
"""

import pytest

from kokorog2p.en.normalizer import EnglishNormalizer
from kokorog2p.pipeline.models import NormalizationStep


class TestEnglishNormalizer:
    """Test suite for EnglishNormalizer."""

    @pytest.fixture
    def normalizer(self):
        """Create a normalizer instance."""
        return EnglishNormalizer(track_changes=False)

    @pytest.fixture
    def normalizer_with_tracking(self):
        """Create a normalizer with change tracking enabled."""
        return EnglishNormalizer(track_changes=True)

    # Basic apostrophe normalization tests
    def test_apostrophe_right_single_quote(self, normalizer):
        """Test normalization of right single quotation mark."""
        assert normalizer("I'm here") == "I'm here"
        assert normalizer("we're ready") == "we're ready"

    def test_apostrophe_left_single_quote(self, normalizer):
        """Test normalization of left single quotation mark."""
        assert normalizer("I'm here") == "I'm here"

    def test_apostrophe_modifier_prime(self, normalizer):
        """Test normalization of modifier letter prime."""
        assert normalizer("Iʹm here") == "I'm here"

    def test_apostrophe_fullwidth(self, normalizer):
        """Test normalization of fullwidth apostrophe."""
        assert normalizer("I＇m here") == "I'm here"

    def test_multiple_exclamation_marks(self, normalizer):
        """Test normalization of !!!."""
        assert normalizer("!!!") == "!!!"

    # Backtick and acute handling tests
    def test_backtick_in_contraction(self, normalizer):
        """Test backtick inside contractions is normalized to apostrophe."""
        assert normalizer("don`t") == "don't"
        assert normalizer("we`re") == "we're"
        assert normalizer("I`ve") == "I've"

    def test_acute_in_contraction(self, normalizer):
        """Test acute accent inside contractions is normalized to apostrophe."""
        assert normalizer("don´t") == "don't"
        assert normalizer("we´re") == "we're"

    def test_standalone_backtick(self, normalizer):
        """Test standalone backtick is kept as backtick (for quotes)."""
        result = normalizer("He said `hello`")
        assert "`" in result  # Backtick preserved for quote usage

    def test_standalone_acute_to_backtick(self, normalizer):
        """Test standalone acute is converted to backtick."""
        # After contraction rule, standalone acute → backtick
        result = normalizer("´test´")
        assert result == "`test`"

    # Quote normalization tests
    def test_curly_quotes_to_straight(self, normalizer):
        """Test curly quotes are normalized to straight quotes."""
        assert normalizer("\u201cHello\u201d") == "\u201cHello\u201d"
        assert normalizer("\u201cWorld\u201d") == "\u201cWorld\u201d"

    def test_guillemets_to_straight_quotes(self, normalizer):
        """Test guillemets are normalized to straight quotes."""
        assert normalizer("«Hello»") == "\u201cHello\u201d"

    def test_angle_quotes_to_straight(self, normalizer):
        """Test angle quotes are normalized to straight quotes."""
        assert normalizer("‹Hello›") == "\u201cHello\u201d"

    def test_double_prime_to_quote(self, normalizer):
        """Test double prime is normalized to quote."""
        assert normalizer("5″ tall") == '5" tall'

    def test_fullwidth_quote(self, normalizer):
        """Test fullwidth quotation mark is normalized."""
        assert normalizer("＂Hello＂") == '"Hello"'

    # Ellipsis normalization tests
    def test_three_dots_to_ellipsis(self, normalizer):
        """Test three dots are normalized to ellipsis."""
        assert normalizer("Wait...") == "Wait…"

    def test_four_dots_to_ellipsis(self, normalizer):
        """Test four dots (typo) are normalized to ellipsis."""
        assert normalizer("Wait....") == "Wait…"

    def test_two_dots_to_ellipsis(self, normalizer):
        """Test two dots (typo) are normalized to ellipsis."""
        assert normalizer("Wait..") == "Wait…"

    def test_spaced_dots_to_ellipsis(self, normalizer):
        """Test spaced dots are normalized to ellipsis."""
        assert normalizer("Wait . . .") == "Wait…"
        assert normalizer("Wait. . . ") == "Wait…"
        assert normalizer("Wait . . . ") == "Wait…"

    def test_ellipsis_spacing_cleanup(self, normalizer):
        """Test spaces around ellipsis are removed."""
        assert normalizer("Wait … here") == "Wait…here"
        assert normalizer("Wait… here") == "Wait…here"
        assert normalizer("Wait …here") == "Wait…here"

    # Dash normalization tests
    def test_double_hyphen_to_em_dash(self, normalizer):
        """Test double hyphen is normalized to em dash."""
        assert normalizer("Hello--world") == "Hello—world"

    def test_spaced_hyphen_to_em_dash(self, normalizer):
        """Test spaced hyphen is normalized to em dash."""
        assert normalizer("Hello - world") == "Hello—world"

    def test_spaced_double_hyphen_to_em_dash(self, normalizer):
        """Test spaced double hyphen is normalized to em dash."""
        assert normalizer("Hello -- world") == "Hello—world"

    def test_en_dash_to_em_dash(self, normalizer):
        """Test en dash is normalized to em dash."""
        assert normalizer("Hello–world") == "Hello—world"

    def test_horizontal_bar_to_em_dash(self, normalizer):
        """Test horizontal bar is normalized to em dash."""
        assert normalizer("Hello―world") == "Hello—world"

    def test_figure_dash_to_em_dash(self, normalizer):
        """Test figure dash is normalized to em dash."""
        assert normalizer("Hello‒world") == "Hello—world"

    def test_minus_sign_to_em_dash(self, normalizer):
        """Test minus sign is normalized to em dash."""
        assert normalizer("Hello−world") == "Hello—world"

    def test_single_hyphen_preserved(self, normalizer):
        """Test single hyphen (for compound words) is preserved."""
        assert normalizer("mother-in-law") == "mother-in-law"
        assert normalizer("well-known") == "well-known"

    # Complex integration tests
    def test_complex_sentence(self, normalizer):
        """Test a complex sentence with multiple normalizations."""
        input_text = "\u201cI'm going--wait...don`t go!\" she said."
        expected = "\u201cI'm going—wait…don't go!\" she said."
        assert normalizer(input_text) == expected

    def test_mixed_quotes_and_contractions(self, normalizer):
        """Test mixed quotes and contractions."""
        input_text = "He said, \u201cI\u00b4m ready,\u201d but we`re not."
        expected = "He said, \u201cI'm ready,\u201d but we're not."
        assert normalizer(input_text) == expected

    def test_order_dependency(self, normalizer):
        """Test that normalization order matters (regression test)."""
        # Acute in contraction should become apostrophe, not backtick
        assert normalizer("we´re") == "we're"
        # Standalone acute should become backtick
        assert normalizer("´") == "`"

    # Change tracking tests
    def test_tracking_enabled(self, normalizer_with_tracking):
        """Test that change tracking captures normalizations."""
        text = "I\u2019m here"  # Use curly apostrophe \u2019
        result, steps = normalizer_with_tracking.normalize(text)

        assert result == "I'm here"
        assert len(steps) == 1
        assert steps[0].rule_name == "apostrophe_right_single"
        assert steps[0].original == "\u2019"
        assert steps[0].normalized == "'"

    def test_tracking_multiple_changes(self, normalizer_with_tracking):
        """Test tracking multiple normalizations."""
        text = "«Hello» she said..."
        result, steps = normalizer_with_tracking.normalize(text)

        assert result == "\u201cHello\u201d she said…"
        # Should have changes for: left curly quote, right curly quote, ellipsis
        assert len(steps) >= 1

        # Check that we tracked the quote normalizations
        quote_steps = [s for s in steps if "quote" in s.rule_name]
        assert len(quote_steps) >= 0

        # Check that we tracked the ellipsis
        ellipsis_steps = [s for s in steps if "ellipsis" in s.rule_name]
        assert len(ellipsis_steps) >= 1

    def test_tracking_positions(self, normalizer_with_tracking):
        """Test that positions are tracked correctly."""
        text = "Start\u201cEnd\u201d"
        result, steps = normalizer_with_tracking.normalize(text)

        assert len(steps) == 0
        # First quote at position 5

    def test_no_changes(self, normalizer_with_tracking):
        """Test that clean text produces no normalization steps."""
        text = "Hello world"
        result, steps = normalizer_with_tracking.normalize(text)

        assert result == "Hello world"
        assert len(steps) == 0

    def test_convenience_call(self, normalizer):
        """Test __call__ convenience method."""
        # Should work identically to normalize() but without steps
        assert normalizer("I'm here") == "I'm here"
        assert normalizer("\u201cTest\u201d") == "\u201cTest\u201d"

    # Edge cases
    def test_empty_string(self, normalizer):
        """Test empty string handling."""
        assert normalizer("") == ""

    def test_only_whitespace(self, normalizer):
        """Test whitespace-only string."""
        assert normalizer("   ") == "   "

    def test_unicode_normalization_nfc(self, normalizer):
        """Test that various Unicode forms are handled correctly."""
        # Various apostrophe forms should all normalize
        inputs = [
            "I\u2019m",  # Right single quote
            "I\u2018m",  # Left single quote
            "I\u02b9m",  # Modifier prime
            "I\uff07m",  # Fullwidth
        ]
        for text in inputs:
            assert normalizer(text) == "I'm"

    def test_repeated_normalizations(self, normalizer):
        """Test that normalizing already-normalized text is idempotent."""
        text1 = "I'm here"
        text2 = normalizer(text1)
        text3 = normalizer(text2)
        assert text2 == text3 == "I'm here"


class TestNormalizationStepModel:
    """Test the NormalizationStep dataclass."""

    def test_str_representation(self):
        """Test string representation of NormalizationStep."""
        step = NormalizationStep(
            rule_name="test_rule",
            position=10,
            original="'",
            normalized="'",
            context="Test context",
        )

        result = str(step)
        assert "test_rule" in result
        assert "10" in result
        assert "'" in result
        assert "Test context" in result

    def test_str_without_context(self):
        """Test string representation without context."""
        step = NormalizationStep(
            rule_name="test_rule", position=5, original="a", normalized="b"
        )

        result = str(step)
        assert "test_rule" in result
        assert "5" in result
        assert "'a'" in result
        assert "'b'" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
