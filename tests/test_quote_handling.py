"""Comprehensive tests for quote handling in kokorog2p."""

import pytest

from kokorog2p.en.g2p import EnglishG2P


class TestQuoteHandling:
    """Test quote direction assignment for various cases."""

    @pytest.fixture
    def g2p(self):
        """Create EnglishG2P instance."""
        return EnglishG2P()

    def _get_quote_directions(self, g2p, text):
        """Helper to extract quote characters and their directions from output."""
        tokens = g2p(text)
        quotes = []
        for token in tokens:
            if token.phonemes in "\u201c\u201d":  # Curly quotes
                direction = "L" if token.phonemes == "\u201c" else "R"
                quotes.append(direction)
        return " ".join(quotes)

    def test_simple_quotes(self, g2p):
        """Test simple quoted phrase: "hello" → L R"""
        text = 'She said "hello"'
        result = self._get_quote_directions(g2p, text)
        assert result == "L R", f"Expected 'L R', got '{result}'"

    def test_multiple_quotes(self, g2p):
        """Test multiple quoted phrases: "one" and "two" → L R L R"""
        text = '"one" and "two"'
        result = self._get_quote_directions(g2p, text)
        assert result == "L R L R", f"Expected 'L R L R', got '{result}'"

    def test_guillemets_simple(self, g2p):
        """Test guillemets converted to curly quotes: «hello» → L R"""
        text = "She said «hello»"
        result = self._get_quote_directions(g2p, text)
        assert result == "L R", f"Expected 'L R', got '{result}'"

    def test_guillemets_nested(self, g2p):
        """Test nested guillemets: «outer «inner» end» → L L R R"""
        text = "He said «She said «yes» to me»"
        result = self._get_quote_directions(g2p, text)
        assert result == "L L R R", f"Expected 'L L R R', got '{result}'"

    def test_backtick_quotes(self, g2p):
        """Test backtick/acute as quotes: `hello´ → L R"""
        text = "She said `hello´"
        result = self._get_quote_directions(g2p, text)
        assert result == "L R", f"Expected 'L R', got '{result}'"

    def test_directional_quote_types(self, g2p):
        """Test mixed quote types with directional quotes normalized to curly.

        Guillemets («»), angle quotes (‹›), and other directional quotes are
        normalized to curly quotes preserving their directionality (L/R).
        """
        text = "«a» «b» ‹c›"
        result = self._get_quote_directions(g2p, text)
        # All directional quotes preserve their directionality
        # Expected: L R L R L R (each pair alternates)
        assert result == "L R L R L R", f"Expected 'L R L R L R', got '{result}'"

    def test_nondirectional_quote_types(self, g2p):
        """Test nondirectional quote types with directional quotes normalized to ".

        Guillemets («»), angle quotes (‹›), and other directional quotes are
        normalized to curly quotes preserving their directionality (L/R).
        """
        text = '"a" "b" "c"'
        result = self._get_quote_directions(g2p, text)
        # All directional quotes preserve their directionality
        # Expected: L R L R L R (each pair alternates)
        assert result == "L R L R L R", f"Expected 'L R L R L R', got '{result}'"

    def test_quotes_with_contractions(self, g2p):
        """Test quotes don't interfere with contractions: "I'm fine" → L R"""
        text = "I'm told \"I'm fine\""
        result = self._get_quote_directions(g2p, text)
        assert result == "L R", f"Expected 'L R', got '{result}'"

        # Check contractions are preserved
        tokens = g2p(text)
        contractions = [t for t in tokens if "'" in t.text]
        assert len(contractions) == 2, "Should have 2 contractions"
        assert all(
            t.phonemes and "'" not in t.phonemes for t in contractions
        ), "Contractions should not have apostrophes in phonemes"

    def test_curly_quotes_input(self, g2p):
        """Test curly quotes in input are handled: "hello" → L R"""
        text = 'She said "hello"'
        result = self._get_quote_directions(g2p, text)
        assert result == "L R", f"Expected 'L R', got '{result}'"

    def test_quote_phoneme_values(self, g2p):
        """Test that quote phonemes are correct Unicode characters."""
        text = '"hello"'
        tokens = g2p(text)

        # Straight quotes converted to curly quotes in token.text
        quotes = [t for t in tokens if t.text in "\u201c\u201d"]
        assert len(quotes) == 2, "Should have 2 quote tokens"

        assert (
            quotes[0].phonemes == "\u201c"
        ), "First quote should be U+201C (left curly)"
        assert (
            quotes[1].phonemes == "\u201d"
        ), "Second quote should be U+201D (right curly)"


class TestQuoteSpacing:
    """Test that quotes don't have extra spaces around them."""

    @pytest.fixture
    def g2p(self):
        """Create EnglishG2P instance."""
        return EnglishG2P()

    def _get_phonemes(self, g2p, text):
        """Helper to get phoneme output as string."""
        tokens = g2p(text)
        return "".join(
            (t.phonemes or "") + (" " if t.whitespace else "") for t in tokens
        ).strip()

    def test_no_space_before_opening_quote(self, g2p):
        """Opening quote should not have space before it."""
        text = 'She said "hello".'
        result = self._get_phonemes(g2p, text)
        assert ' "' not in result, "Should not have space before opening quote"

    def test_no_space_after_closing_quote(self, g2p):
        """Closing quote should not have space after it before punctuation."""
        text = 'She said "hello".'
        result = self._get_phonemes(g2p, text)
        assert '" ' not in result or result.endswith(
            '" '
        ), "Should not have space after closing quote before punctuation"

    def test_quotes_directly_around_word(self, g2p):
        """Quotes should be directly around the word with no spaces."""
        text = '"hello"'
        result = self._get_phonemes(g2p, text)
        # Should be "həlˈO" not " həlˈO " or " həlˈO" or "həlˈO "
        assert (
            "\u201chəlˈO\u201d" in result
        ), f"Quotes should be directly around word, got: {repr(result)}"
