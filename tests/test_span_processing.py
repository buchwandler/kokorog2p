"""Tests for span-based override processing."""

from kokorog2p.span_processing import apply_overrides_to_tokens, parse_ssmd_to_spans
from kokorog2p.types import OverrideSpan, TokenSpan


class TestParseSSMDToSpans:
    """Tests for parse_ssmd_to_spans function."""

    def test_simple_annotation(self):
        """Test simple SSMD annotation converts to span."""
        clean, spans, warnings = parse_ssmd_to_spans('[Hello]{ph="hɛloʊ"}')
        assert clean == "Hello"
        assert len(spans) == 1
        assert spans[0].char_start == 0
        assert spans[0].char_end == 5
        assert spans[0].attrs["ph"] == "hɛloʊ"
        assert len(warnings) == 0

    def test_annotation_with_surrounding_text(self):
        """Test annotation with text before and after."""
        clean, spans, warnings = parse_ssmd_to_spans('Say [Hello]{ph="hɛloʊ"} world!')
        assert clean == "Say Hello world!"
        assert len(spans) == 1
        assert spans[0].char_start == 4  # After "Say "
        assert spans[0].char_end == 9  # "Hello" is 5 chars
        assert spans[0].attrs["ph"] == "hɛloʊ"
        assert len(warnings) == 0

    def test_multiple_annotations(self):
        """Test multiple annotations in same text."""
        clean, spans, warnings = parse_ssmd_to_spans(
            '[Hello]{ph="hɛloʊ"} [world]{ph="wɝld"}!'
        )
        assert clean == "Hello world!"
        assert len(spans) == 2
        assert spans[0].char_start == 0
        assert spans[0].char_end == 5
        assert spans[0].attrs["ph"] == "hɛloʊ"
        assert spans[1].char_start == 6
        assert spans[1].char_end == 11
        assert spans[1].attrs["ph"] == "wɝld"
        assert len(warnings) == 0

    def test_duplicate_words(self):
        """Test that duplicate words get separate spans with correct offsets."""
        clean, spans, warnings = parse_ssmd_to_spans(
            'The [the]{ph="ðə"} and [the]{ph="ði"} end'
        )
        assert clean == "The the and the end"
        assert len(spans) == 2
        # First "the" at position 4-7
        assert spans[0].char_start == 4
        assert spans[0].char_end == 7
        assert spans[0].attrs["ph"] == "ðə"
        # Second "the" at position 12-15
        assert spans[1].char_start == 12
        assert spans[1].char_end == 15
        assert spans[1].attrs["ph"] == "ði"
        assert len(warnings) == 0

    def test_punctuation_adjacent(self):
        """Test annotation with adjacent punctuation."""
        clean, spans, warnings = parse_ssmd_to_spans('[Hello]{ph="hɛloʊ"}, world!')
        assert clean == "Hello, world!"
        assert len(spans) == 1
        assert spans[0].char_start == 0
        assert spans[0].char_end == 5  # "Hello" only, not comma
        assert len(warnings) == 0

    def test_multiple_attributes(self):
        """Test annotation with multiple attributes."""
        clean, spans, warnings = parse_ssmd_to_spans(
            '[Bonjour]{ph="bɔ̃ʒuʁ" lang="fr"} monde'
        )
        assert clean == "Bonjour monde"
        assert len(spans) == 1
        assert spans[0].attrs["ph"] == "bɔ̃ʒuʁ"
        assert spans[0].attrs["lang"] == "fr"
        assert len(warnings) == 0

    def test_single_quotes(self):
        """Test annotation with single quotes."""
        clean, spans, warnings = parse_ssmd_to_spans("[Hello]{ph='hɛloʊ'}")
        assert clean == "Hello"
        assert len(spans) == 1
        assert spans[0].attrs["ph"] == "hɛloʊ"
        assert len(warnings) == 0

    def test_no_annotations(self):
        """Test plain text without annotations."""
        clean, spans, warnings = parse_ssmd_to_spans("Hello world!")
        assert clean == "Hello world!"
        assert len(spans) == 0
        assert len(warnings) == 0

    def test_empty_attributes(self):
        """Test annotation with empty braces."""
        clean, spans, warnings = parse_ssmd_to_spans("[Hello]{}")
        assert clean == "Hello"
        assert len(spans) == 0  # No attrs, so no span created
        assert len(warnings) == 0


class TestApplyOverridesToTokens:
    """Tests for apply_overrides_to_tokens function."""

    def test_exact_match_single_token(self):
        """Test override that exactly matches one token."""
        tokens = [TokenSpan("Hello", 0, 5), TokenSpan("world", 6, 11)]
        overrides = [OverrideSpan(0, 5, {"ph": "hɛloʊ"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert len(result_tokens) == 2
        assert result_tokens[0].meta["ph"] == "hɛloʊ"
        assert result_tokens[0].meta["rating"] == 5
        assert "ph" not in result_tokens[1].meta
        assert len(warnings) == 0

    def test_exact_match_multiple_tokens(self):
        """Test override that exactly spans multiple tokens."""
        tokens = [
            TokenSpan("Hello", 0, 5),
            TokenSpan("world", 6, 11),
            TokenSpan("!", 11, 12),
        ]
        overrides = [OverrideSpan(0, 11, {"ph": "hɛloʊ wɝld"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert result_tokens[0].meta["ph"] == "hɛloʊ wɝld"
        assert result_tokens[1].meta["ph"] == "hɛloʊ wɝld"
        assert "ph" not in result_tokens[2].meta
        assert len(warnings) == 0

    def test_duplicate_words_separate_spans(self):
        """Test that duplicate words are handled correctly with separate overrides."""
        tokens = [
            TokenSpan("The", 0, 3),
            TokenSpan("the", 4, 7),
            TokenSpan("and", 8, 11),
            TokenSpan("the", 12, 15),
        ]
        overrides = [
            OverrideSpan(4, 7, {"ph": "ðə"}),  # First "the"
            OverrideSpan(12, 15, {"ph": "ði"}),  # Second "the"
        ]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert "ph" not in result_tokens[0].meta  # "The" - no override
        assert result_tokens[1].meta["ph"] == "ðə"  # First "the"
        assert "ph" not in result_tokens[2].meta  # "and" - no override
        assert result_tokens[3].meta["ph"] == "ði"  # Second "the"
        assert len(warnings) == 0

    def test_punctuation_not_included(self):
        """Test that punctuation tokens don't get overridden when not in span."""
        tokens = [
            TokenSpan("Hello", 0, 5),
            TokenSpan(",", 5, 6),
            TokenSpan("world", 7, 12),
        ]
        overrides = [OverrideSpan(0, 5, {"ph": "hɛloʊ"})]  # Only "Hello", not comma

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert result_tokens[0].meta["ph"] == "hɛloʊ"
        assert "ph" not in result_tokens[1].meta  # Comma not overridden
        assert "ph" not in result_tokens[2].meta
        assert len(warnings) == 0

    def test_language_override(self):
        """Test language attribute application."""
        tokens = [TokenSpan("Bonjour", 0, 7)]
        overrides = [OverrideSpan(0, 7, {"lang": "fr"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert result_tokens[0].lang == "fr"
        assert len(warnings) == 0

    def test_both_phoneme_and_language(self):
        """Test both phoneme and language overrides."""
        tokens = [TokenSpan("Bonjour", 0, 7)]
        overrides = [OverrideSpan(0, 7, {"ph": "bɔ̃ʒuʁ", "lang": "fr"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert result_tokens[0].meta["ph"] == "bɔ̃ʒuʁ"
        assert result_tokens[0].lang == "fr"
        assert len(warnings) == 0

    def test_partial_overlap_snap_mode(self):
        """Test partial overlap in snap mode."""
        tokens = [TokenSpan("Hello", 0, 5), TokenSpan("world", 6, 11)]
        # Override starts mid-token
        overrides = [OverrideSpan(2, 11, {"ph": "test"})]

        result_tokens, warnings = apply_overrides_to_tokens(
            tokens, overrides, mode="snap"
        )

        # Should snap to both tokens and emit warning
        assert result_tokens[0].meta["ph"] == "test"
        assert result_tokens[1].meta["ph"] == "test"
        assert len(warnings) == 1
        assert "snapping" in warnings[0].lower()

    def test_partial_overlap_strict_mode(self):
        """Test partial overlap in strict mode."""
        tokens = [TokenSpan("Hello", 0, 5), TokenSpan("world", 6, 11)]
        # Override starts mid-token
        overrides = [OverrideSpan(2, 11, {"ph": "test"})]

        result_tokens, warnings = apply_overrides_to_tokens(
            tokens, overrides, mode="strict"
        )

        # Should skip override and emit warning
        assert "ph" not in result_tokens[0].meta
        assert "ph" not in result_tokens[1].meta
        assert len(warnings) == 1
        assert "skipping" in warnings[0].lower()

    def test_no_overlap_warning(self):
        """Test override with no overlapping tokens."""
        tokens = [TokenSpan("Hello", 0, 5)]
        overrides = [OverrideSpan(10, 15, {"ph": "test"})]  # Outside token range

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert "ph" not in result_tokens[0].meta
        assert len(warnings) == 1
        assert "does not overlap" in warnings[0]

    def test_multiple_overrides_same_token(self):
        """Test multiple overrides on same token (last wins)."""
        tokens = [TokenSpan("test", 0, 4)]
        overrides = [
            OverrideSpan(0, 4, {"ph": "first"}),
            OverrideSpan(0, 4, {"ph": "second"}),
        ]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        # Second override should win
        assert result_tokens[0].meta["ph"] == "second"
        assert len(warnings) == 0

    def test_custom_attributes(self):
        """Test that custom (non-ph, non-lang) attributes are stored in meta."""
        tokens = [TokenSpan("test", 0, 4)]
        overrides = [OverrideSpan(0, 4, {"rate": "fast", "volume": "loud"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert result_tokens[0].meta["rate"] == "fast"
        assert result_tokens[0].meta["volume"] == "loud"
        assert len(warnings) == 0

    def test_empty_tokens(self):
        """Test with no tokens."""
        tokens: list[TokenSpan] = []
        overrides = [OverrideSpan(0, 5, {"ph": "test"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert len(result_tokens) == 0
        assert len(warnings) == 1
        assert "does not overlap" in warnings[0]

    def test_empty_overrides(self):
        """Test with no overrides."""
        tokens = [TokenSpan("Hello", 0, 5)]
        overrides: list[OverrideSpan] = []

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert len(result_tokens) == 1
        assert "ph" not in result_tokens[0].meta
        assert len(warnings) == 0
