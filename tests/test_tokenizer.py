"""Unit tests for the tokenization framework.

Tests the BaseTokenizer, RegexTokenizer, and SpacyTokenizer classes.
"""

import pytest

from kokorog2p import get_g2p, reset_abbreviations
from kokorog2p.pipeline.tokenizer import RegexTokenizer, SpacyTokenizer


class TestRegexTokenizer:
    """Test suite for RegexTokenizer."""

    @pytest.fixture
    def tokenizer(self):
        """Create a regex tokenizer instance."""
        return RegexTokenizer(track_positions=True, use_bracket_matching=True)

    @pytest.fixture
    def tokenizer_simple_quotes(self):
        """Create a regex tokenizer with simple quote alternation."""
        return RegexTokenizer(track_positions=True, use_bracket_matching=False)

    def test_simple_sentence(self, tokenizer):
        """Test tokenizing a simple sentence."""
        tokens = tokenizer.tokenize("Hello world")

        assert len(tokens) == 2
        assert tokens[0].text == "Hello"
        assert tokens[1].text == "world"
        assert tokens[0].whitespace == " "

    def test_punctuation_split(self, tokenizer):
        """Test that punctuation is split into separate tokens."""
        tokens = tokenizer.tokenize("Hello, world!")

        assert len(tokens) == 4
        assert tokens[0].text == "Hello"
        assert tokens[1].text == ","
        assert tokens[2].text == "world"
        assert tokens[3].text == "!"

    def test_contraction_not_split(self, tokenizer):
        """Test that contractions are kept as single tokens."""
        tokens = tokenizer.tokenize("I'm here, don't go")

        # Should be: ["I'm", "here", ",", "don't", "go"]
        assert len(tokens) == 5
        assert tokens[0].text == "I'm"
        assert tokens[3].text == "don't"

    def test_abbreviation_not_split(self, tokenizer):
        """Test that abbreviations with periods are preserved."""
        tokens = tokenizer.tokenize("Hello Mr. Smith")

        assert len(tokens) == 3
        assert tokens[0].text == "Hello"
        assert tokens[1].text == "Mr."
        assert tokens[2].text == "Smith"
        assert tokens[1].char_start == 6
        assert tokens[1].char_end == 9

    def test_custom_abbreviation_merge(self):
        """Tokenization should reflect custom abbreviations."""
        reset_abbreviations()
        g2p = get_g2p("en-us", use_spacy=False)
        g2p.add_abbreviation("X.Y.", "Ex Why")

        tokenizer = RegexTokenizer(
            track_positions=True, use_bracket_matching=True, lang="en-us"
        )
        tokens = tokenizer.tokenize("X.Y.")
        assert [t.text for t in tokens] == ["X.Y."]
        assert tokens[0].char_start == 0
        assert tokens[0].char_end == 4

        reset_abbreviations()

    def test_position_tracking(self, tokenizer):
        """Test that character positions are tracked correctly."""
        tokens = tokenizer.tokenize("Hello world")

        assert tokens[0].char_start == 0
        assert tokens[0].char_end == 5
        assert tokens[1].char_start == 6
        assert tokens[1].char_end == 11

    def test_whitespace_handling(self, tokenizer):
        """Test that whitespace is attached to previous token."""
        tokens = tokenizer.tokenize("Hello   world")

        assert len(tokens) == 2
        assert tokens[0].whitespace == "   "
        assert tokens[1].whitespace == ""

    def test_bracket_matching_quotes_simple(self, tokenizer):
        """Test bracket-matching quote algorithm with simple quotes."""
        tokens = tokenizer.tokenize('"Hello" world')

        # Find quote tokens
        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        assert len(quote_tokens) == 2
        # First quote should be opening (left curly)
        assert quote_tokens[0].text == "\u201c"
        assert quote_tokens[0].quote_depth == 1
        # Second quote should be closing (right curly)
        assert quote_tokens[1].text == "\u201d"
        assert quote_tokens[1].quote_depth == 0

    def test_bracket_matching_nested_quotes(self, tokenizer):
        """Test bracket-matching with nested quotes."""
        tokens = tokenizer.tokenize('"She said `hello` to me"')

        # Should handle nested quotes properly
        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        # Outer quotes at depth 1, inner quotes at depth 2
        assert len(quote_tokens) >= 4
        # First " opens (depth 1)
        assert quote_tokens[0].quote_depth == 1
        # First ` opens (depth 2)
        assert quote_tokens[1].quote_depth == 2
        # Second ` closes (depth 2)
        assert quote_tokens[2].quote_depth == 1
        # Second " closes (depth 1)
        assert quote_tokens[3].quote_depth == 0

    def test_simple_alternating_quotes(self, tokenizer_simple_quotes):
        """Test simple alternation without nesting support."""
        tokens = tokenizer_simple_quotes.tokenize('"Hello" world')

        # Should use simple alternation
        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        assert len(quote_tokens) == 2
        # Both quotes should have depth 1
        assert quote_tokens[0].quote_depth == 1
        assert quote_tokens[1].quote_depth == 0

    def test_normalize_phoneme_quotes_ascii(self):
        """Curly quotes should normalize to ASCII when requested."""
        tokenizer = RegexTokenizer(phoneme_quotes="ascii")
        text = "\u201cHello\u201d"
        assert tokenizer.normalize_phoneme_quotes(text) == '"Hello"'

    def test_normalize_phoneme_quotes_none(self):
        """Quote characters should be stripped when requested."""
        tokenizer = RegexTokenizer(phoneme_quotes="none")
        text = "\u201cHello\u201d"
        assert tokenizer.normalize_phoneme_quotes(text) == "Hello"

    def test_empty_string(self, tokenizer):
        """Test tokenizing empty string."""
        tokens = tokenizer.tokenize("")
        assert len(tokens) == 0

    def test_only_punctuation(self, tokenizer):
        """Test tokenizing only punctuation."""
        tokens = tokenizer.tokenize(".,;!")

        assert len(tokens) == 4
        assert all(len(t.text) == 1 for t in tokens)

    def test_multiple_words_with_contractions(self, tokenizer):
        """Test a complex sentence with multiple contractions."""
        tokens = tokenizer.tokenize("I'm sure we're ready, don't you think?")

        # Count contraction tokens
        contractions = [t for t in tokens if "'" in t.text]
        assert len(contractions) == 3
        assert "I'm" in [t.text for t in contractions]
        assert "we're" in [t.text for t in contractions]
        assert "don't" in [t.text for t in contractions]


class TestSpacyTokenizer:
    """Test suite for SpacyTokenizer."""

    @pytest.fixture
    def spacy_nlp(self):
        """Load spaCy model if available."""
        try:
            import spacy

            return spacy.load("en_core_web_sm")
        except (ImportError, OSError):
            pytest.skip("spaCy not available or model not installed")

    @pytest.fixture
    def tokenizer(self, spacy_nlp):
        """Create a spaCy tokenizer instance."""
        return SpacyTokenizer(
            nlp=spacy_nlp, track_positions=True, use_bracket_matching=True
        )

    def test_simple_sentence_with_pos(self, tokenizer):
        """Test that POS tags are assigned."""
        tokens = tokenizer.tokenize("Hello world")

        assert len(tokens) == 2
        assert tokens[0].text == "Hello"
        assert tokens[1].text == "world"
        # Should have POS tags
        assert tokens[0].pos_tag != ""
        assert tokens[1].pos_tag != ""

    def test_punctuation_pos_tags(self, tokenizer):
        """Test that punctuation gets appropriate POS tags."""
        tokens = tokenizer.tokenize("Hello, world!")

        # Find punctuation tokens
        punct_tokens = [t for t in tokens if t.text in (",", "!")]

        assert len(punct_tokens) == 2
        # Punctuation should have specific tags
        for token in punct_tokens:
            assert token.pos_tag in (".", ",", "!", "?", ":", ";")

    def test_contraction_tokenization(self, tokenizer):
        """Test that contractions are handled correctly."""
        tokens = tokenizer.tokenize("I'm here")

        # spaCy typically splits contractions differently than regex
        # Just verify we get tokens
        assert len(tokens) >= 2

    def test_spacy_quote_tags(self, tokenizer):
        """Test that spaCy's quote tags are converted correctly."""
        tokens = tokenizer.tokenize('"Hello world"')

        # Should convert spaCy's `` and '' tags to curly quotes
        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d", '"')]
        assert len(quote_tokens) >= 2

    def test_position_tracking_with_spacy(self, tokenizer):
        """Test that positions are tracked with spaCy."""
        tokens = tokenizer.tokenize("Hello world")

        # spaCy provides accurate character positions
        assert tokens[0].char_start == 0
        assert tokens[0].char_end == 5
        assert tokens[1].char_start == 6
        assert tokens[1].char_end == 11


class TestQuoteDetection:
    """Test suite specifically for quote detection algorithms."""

    @pytest.fixture
    def bracket_tokenizer(self):
        """Tokenizer with bracket-matching quotes."""
        return RegexTokenizer(track_positions=False, use_bracket_matching=True)

    @pytest.fixture
    def simple_tokenizer(self):
        """Tokenizer with simple alternating quotes."""
        return RegexTokenizer(track_positions=False, use_bracket_matching=False)

    def test_nested_quotes_bracket_matching(self, bracket_tokenizer):
        """Test that nested quotes are handled correctly."""
        # Use different quote types for proper nesting: " and `
        text = '"Outer `inner` text"'
        tokens = bracket_tokenizer.tokenize(text)

        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        # Should have 4 quote tokens with proper depths
        assert len(quote_tokens) == 4
        # Depths should be: 1 ("), 2 (`), 2 (`), 1 (")
        depths = [t.quote_depth for t in quote_tokens]
        assert depths == [1, 2, 1, 0]

    def test_nested_quotes_simple_alternation(self, simple_tokenizer):
        """Test that simple alternation doesn't handle nesting."""
        text = '"Outer "inner" text"'
        tokens = simple_tokenizer.tokenize(text)

        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        # Simple alternation treats all quotes at same level
        assert len(quote_tokens) == 4
        # All quotes should alternate between depth 1 and 0
        # (depending on implementation details)

    def test_mixed_quote_types(self, bracket_tokenizer):
        """Test mixing double quotes and backticks."""
        text = '"She said `hello` loudly"'
        tokens = bracket_tokenizer.tokenize(text)

        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        # Should handle different quote types with bracket matching
        assert len(quote_tokens) >= 4

    def test_unmatched_quotes(self, bracket_tokenizer):
        """Test handling of unmatched quotes."""
        text = '"Hello world'  # Missing closing quote
        tokens = bracket_tokenizer.tokenize(text)

        # Should still tokenize without errors
        assert len(tokens) >= 2

    def test_empty_quotes(self, bracket_tokenizer):
        """Test empty quoted string."""
        text = '""'
        tokens = bracket_tokenizer.tokenize(text)

        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]
        assert len(quote_tokens) == 2

    def test_multiple_quote_pairs(self, bracket_tokenizer):
        """Test multiple separate quoted strings."""
        text = '"First" and "second"'
        tokens = bracket_tokenizer.tokenize(text)

        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        # Should have 4 quotes (2 pairs)
        assert len(quote_tokens) == 4
        assert quote_tokens[0].quote_depth == 1
        assert quote_tokens[1].quote_depth == 0
        assert quote_tokens[2].quote_depth == 1
        assert quote_tokens[3].quote_depth == 0

    def test_nested_quotes(self, bracket_tokenizer):
        """Test deeply nested quotes with different quote types."""
        # Use alternating quote types for proper nesting
        text = '"Level1 `Level2 text` done"'
        tokens = bracket_tokenizer.tokenize(text)

        quote_tokens = [t for t in tokens if t.text in ("\u201c", "\u201d")]

        # Should handle 3 levels of nesting
        depths = [t.quote_depth for t in quote_tokens]
        # " opens (1), ` opens (2), " opens (3), closes (3,2,1)
        assert max(depths) == 2


class TestTokenizerEdgeCases:
    """Test edge cases for tokenizers."""

    @pytest.fixture
    def tokenizer(self):
        """Create a regex tokenizer."""
        return RegexTokenizer()

    def test_unicode_text(self, tokenizer):
        """Test tokenizing Unicode text."""
        tokens = tokenizer.tokenize("Héllo wörld")

        assert len(tokens) == 2
        assert tokens[0].text == "Héllo"
        assert tokens[1].text == "wörld"

    def test_numbers(self, tokenizer):
        """Test tokenizing numbers."""
        tokens = tokenizer.tokenize("I have 42 apples")

        assert len(tokens) == 4
        assert tokens[2].text == "42"

    def test_hyphenated_words(self, tokenizer):
        """Test that hyphenated words are split."""
        tokens = tokenizer.tokenize("mother-in-law")

        # Hyphens are treated as punctuation
        assert len(tokens) == 5
        assert tokens[0].text == "mother"
        assert tokens[1].text == "-"
        assert tokens[2].text == "in"
        assert tokens[3].text == "-"
        assert tokens[4].text == "law"

    def test_ellipsis(self, tokenizer):
        """Test tokenizing ellipsis."""
        tokens = tokenizer.tokenize("Wait…")

        assert len(tokens) == 2
        assert tokens[0].text == "Wait"
        assert tokens[1].text == "…"

    def test_em_dash(self, tokenizer):
        """Test tokenizing em dash."""
        tokens = tokenizer.tokenize("Hello—world")

        assert len(tokens) == 3
        assert tokens[0].text == "Hello"
        assert tokens[1].text == "—"
        assert tokens[2].text == "world"

    def test_exclamation_mark(self, tokenizer):
        """Test that multiple exclamation marks are not changed."""
        tokens = tokenizer.tokenize("!!!")

        assert len(tokens) == 3
        assert tokens[0].text == "!"
        assert tokens[1].text == "!"
        assert tokens[2].text == "!"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
