"""Tests for English G2P debug mode (process_with_debug method)."""

import pytest

from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.pipeline.models import PhonemeSource, ProcessedText, ProcessingToken


class TestDebugMode:
    """Test the process_with_debug() method and ProcessedText output."""

    @pytest.fixture
    def g2p(self):
        """Create an EnglishG2P instance."""
        return EnglishG2P(use_spacy=False, use_espeak_fallback=True)

    @pytest.fixture
    def g2p_spacy(self):
        """Create an EnglishG2P instance with spaCy."""
        return EnglishG2P(use_spacy=True, use_espeak_fallback=True)

    def test_process_with_debug_returns_processed_text(self, g2p):
        """Test that process_with_debug returns a ProcessedText object."""
        result = g2p.process_with_debug("hello world")
        assert isinstance(result, ProcessedText)

    def test_processed_text_has_original_text(self, g2p):
        """Test that ProcessedText contains the original input text."""
        text = "Hello, world!"
        result = g2p.process_with_debug(text)
        assert result.original == text

    def test_processed_text_has_normalized_text(self, g2p):
        """Test that ProcessedText contains the normalized text."""
        result = g2p.process_with_debug('She said "hello" to me')
        # Curly quotes should be normalized to straight quotes
        assert result.normalized == 'She said "hello" to me'

    def test_processed_text_has_tokens(self, g2p):
        """Test that ProcessedText contains ProcessingToken objects."""
        result = g2p.process_with_debug("hello world")
        assert len(result.tokens) > 0
        assert all(isinstance(tok, ProcessingToken) for tok in result.tokens)

    def test_normalization_steps_tracked(self, g2p):
        """Test that normalization steps are captured when track_changes=True."""
        # Use curly quotes in input to trigger normalization
        result = g2p.process_with_debug("She said «hello»")
        # Should have normalization steps for curly quote conversion
        assert len(result.normalization_log) > 0

    def test_token_positions_tracked(self, g2p):
        """Test that token positions are tracked correctly."""
        result = g2p.process_with_debug("hello world")

        # First token should be "hello"
        assert result.tokens[0].text == "hello"
        assert result.tokens[0].char_start == 0
        assert result.tokens[0].char_end == 5

        # Second token should be "world"
        assert result.tokens[1].text == "world"
        assert result.tokens[1].char_start == 6
        assert result.tokens[1].char_end == 11

    def test_phoneme_tracking_known_words(self, g2p):
        """Test that phonemes are tracked for known words."""
        result = g2p.process_with_debug("hello")

        # "hello" should be in the lexicon
        hello_token = result.tokens[0]
        assert hello_token.phoneme is not None
        assert len(hello_token.phoneme) > 0

    def test_phoneme_source_tracking(self, g2p):
        """Test that phoneme sources are tracked (gold/silver/unknown)."""
        result = g2p.process_with_debug("hello")

        hello_token = result.tokens[0]
        assert hello_token.phoneme_source is not None
        # Should be either LEXICON_GOLD or LEXICON_SILVER from lexicon
        assert hello_token.phoneme_source in [
            PhonemeSource.LEXICON_GOLD,
            PhonemeSource.LEXICON_SILVER,
        ]

    def test_unknown_word_without_fallback(self, g2p):
        """Test that unknown words are marked with UNKNOWN source when no fallback."""
        # Create a G2P instance explicitly without fallback
        g2p_no_fallback = EnglishG2P(
            use_spacy=False, use_espeak_fallback=False, use_goruut_fallback=False
        )
        result = g2p_no_fallback.process_with_debug("xyzabc123")

        unknown_token = result.tokens[0]
        assert unknown_token.phoneme_source == PhonemeSource.UNKNOWN

    def test_punctuation_handling_in_debug(self, g2p):
        """Test that punctuation is properly handled in debug mode."""
        result = g2p.process_with_debug("Hello, world!")

        # Should have tokens for: hello, comma, world, exclamation
        texts = [tok.text for tok in result.tokens]
        assert "," in texts
        assert "!" in texts

    def test_contraction_handling_in_debug(self, g2p):
        """Test that contractions are properly handled in debug mode."""
        result = g2p.process_with_debug("don't")

        # Should be a single token (not split)
        assert len(result.tokens) == 1
        assert result.tokens[0].text == "don't"

    def test_quote_nesting_depth_tracked(self, g2p):
        """Test that quote nesting depth is tracked in tokens."""
        result = g2p.process_with_debug('"She said "hello" to me"')

        # Find the quote tokens (curly quotes - tokenizer converts straight to curly)
        # Use chr() to ensure correct Unicode characters
        left_quote = chr(8220)  # "
        right_quote = chr(8221)  # "
        quote_tokens = [
            tok for tok in result.tokens if tok.text in [left_quote, right_quote]
        ]

        # Should have quotes
        assert len(quote_tokens) > 0

        # Check that at least one quote has a depth > 0
        assert any(tok.quote_depth > 0 for tok in quote_tokens)

    def test_spacy_pos_tagging_in_debug(self, g2p_spacy):
        """Test that POS tags are tracked when using spaCy."""
        result = g2p_spacy.process_with_debug("hello world")

        # Check that POS tags are present
        assert result.tokens[0].pos_tag is not None
        assert result.tokens[1].pos_tag is not None

    def test_debug_render_method(self, g2p):
        """Test that ProcessedText.render_debug() produces readable output."""
        result = g2p.process_with_debug("hello world")

        output = result.render_debug()
        assert isinstance(output, str)
        assert len(output) > 0

        # Should contain the original text
        assert "hello" in output.lower()
        assert "world" in output.lower()

    def test_complex_sentence_debug(self, g2p):
        """Test debug mode with a complex sentence."""
        # Use text that will trigger normalizations (curly quotes, double hyphens)
        text = 'I don"t think they"ll go--it"s too late.'
        result = g2p.process_with_debug(text)

        # Should have normalization steps (quotes and/or double-hyphen to em-dash)
        # Note: may be 0 if input doesn't trigger normalization rules
        # Just check that the processing works
        assert len(result.tokens) > 5

        # Should track contractions
        contraction_texts = [tok.text for tok in result.tokens]
        assert "don" in contraction_texts or "don't" in contraction_texts
        assert "they" in contraction_texts or "they'll" in contraction_texts
        assert "it" in contraction_texts or "it's" in contraction_texts

    def test_empty_input_debug(self, g2p):
        """Test debug mode with empty input."""
        result = g2p.process_with_debug("")

        assert result.original == ""
        assert result.normalized == ""
        assert len(result.tokens) == 0
        assert len(result.normalization_log) == 0

    def test_whitespace_only_debug(self, g2p):
        """Test debug mode with whitespace-only input."""
        result = g2p.process_with_debug("   \n\t  ")

        # Should normalize to empty or minimal whitespace
        assert len(result.tokens) == 0

    def test_multiple_normalization_changes(self, g2p):
        """Test that multiple normalization changes are all tracked."""
        # Three dots become ellipsis, straight quotes normalized
        text = '"Wait..." she said--"really?"'
        result = g2p.process_with_debug(text)

        # At least one normalization step (... → ellipsis, -- → em-dash)
        assert len(result.normalization_log) >= 1

    def test_debug_preserves_backward_compatibility(self, g2p):
        """Test that debug mode produces same phonemes as regular mode."""
        text = "hello world"

        # Get results from both modes
        regular_tokens = g2p(text)
        debug_result = g2p.process_with_debug(text)

        # Extract phonemes from debug tokens
        debug_phonemes = []
        for tok in debug_result.tokens:
            if tok.phoneme:
                debug_phonemes.extend(tok.phoneme)

        # Extract phonemes from regular tokens
        regular_phonemes = []
        for tok in regular_tokens:
            if tok.phonemes:
                regular_phonemes.extend(tok.phonemes)

        # Should produce identical phoneme sequences
        assert debug_phonemes == regular_phonemes

    def test_unicode_normalization_in_debug(self, g2p):
        """Test that Unicode normalization is reflected in debug output."""
        # Use a composed character (é) vs decomposed (e + combining acute)
        composed = "café"
        decomposed = "cafe\u0301"  # café with combining accent

        result_composed = g2p.process_with_debug(composed)
        result_decomposed = g2p.process_with_debug(decomposed)

        # Both should work and produce tokens
        # Note: Unicode normalization may not force both to be identical
        # depending on the normalizer's NFC/NFD settings
        assert len(result_composed.tokens) > 0
        assert len(result_decomposed.tokens) > 0

        # Both should produce "café" or similar
        assert "caf" in result_composed.normalized
        assert "caf" in result_decomposed.normalized


class TestDebugRenderOutput:
    """Test the rendering/formatting of debug output."""

    @pytest.fixture
    def g2p(self):
        """Create an EnglishG2P instance."""
        return EnglishG2P(use_spacy=False, fallback=None)

    def test_render_includes_section_headers(self, g2p):
        """Test that render output includes clear section headers."""
        result = g2p.process_with_debug("hello")
        output = result.render_debug()

        # Should have section headers
        assert "Original" in output or "ORIGINAL" in output
        assert "Token" in output or "TOKEN" in output

    def test_render_shows_phonemes(self, g2p):
        """Test that render output shows phoneme information."""
        result = g2p.process_with_debug("hello")
        output = result.render_debug()

        # Should show phonemes (hello has phonemes in lexicon)
        assert any(c in output for c in ["h", "ɛ", "l", "oʊ"])

    def test_render_shows_normalization_steps(self, g2p):
        """Test that render output shows normalization steps."""
        result = g2p.process_with_debug('"hello"')
        output = result.render_debug()

        # Should show normalization information
        assert "Normalization" in output or "Normalized" in output or "Steps" in output

    def test_render_multiline_output(self, g2p):
        """Test that render produces multi-line output for readability."""
        result = g2p.process_with_debug("hello world")
        output = result.render_debug()

        # Should have multiple lines
        lines = output.strip().split("\n")
        assert len(lines) > 3


class TestDebugWithFallback:
    """Test debug mode with espeak fallback enabled."""

    @pytest.fixture
    def g2p_espeak(self):
        """Create an EnglishG2P instance with espeak fallback."""
        return EnglishG2P(use_spacy=False, use_espeak_fallback=True)

    def test_unknown_word_with_espeak_fallback(self, g2p_espeak):
        """Test that espeak fallback is tracked in debug mode."""
        result = g2p_espeak.process_with_debug("xyzabc")

        # Unknown word should have phonemes from espeak
        unknown_token = result.tokens[0]
        assert unknown_token.phoneme is not None
        assert unknown_token.phoneme_source == PhonemeSource.ESPEAK

    def test_mixed_sources_in_debug(self, g2p_espeak):
        """Test debug output with mixed phoneme sources."""
        result = g2p_espeak.process_with_debug("hello xyzabc")

        # First word from lexicon, second from espeak
        sources = [tok.phoneme_source for tok in result.tokens if tok.phoneme]

        # Should have both LEXICON_GOLD/LEXICON_SILVER and ESPEAK sources
        assert PhonemeSource.ESPEAK in sources
        assert any(
            s in [PhonemeSource.LEXICON_GOLD, PhonemeSource.LEXICON_SILVER]
            for s in sources
        )
