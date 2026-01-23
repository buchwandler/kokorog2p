"""Tests for span-based override processing."""

from kokorog2p.span_processing import apply_overrides_to_tokens
from kokorog2p.types import OverrideSpan, TokenSpan


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
        assert len(result_tokens) == 2

        assert result_tokens[0].meta["ph"] == "hɛloʊ wɝld"
        assert "ph" not in result_tokens[1].meta
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
        assert len(result_tokens) == 1
        # Should snap to both tokens and emit warning
        assert result_tokens[0].meta["ph"] == "test"
        assert len(warnings) == 1
        assert "snapping" in warnings[0].lower()
        assert "Hello" in warnings[0]
        assert "[0:5]" in warnings[0]

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
        assert "Hello" in warnings[0]
        assert "[0:5]" in warnings[0]

    def test_no_overlap_warning(self):
        """Test override with no overlapping tokens."""
        tokens = [TokenSpan("Hello", 0, 5)]
        overrides = [OverrideSpan(10, 15, {"ph": "test"})]  # Outside token range

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert "ph" not in result_tokens[0].meta
        assert len(warnings) == 1
        assert "does not overlap" in warnings[0]
        assert "[10:15]" in warnings[0]

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


class TestGoldenEdgeCases:
    """Golden tests for complex edge cases (K2P-5)."""

    def test_punctuation_within_override_span(self):
        """Test override span that includes punctuation tokens."""
        tokens = [
            TokenSpan("New", 0, 3),
            TokenSpan("York", 4, 8),
            TokenSpan("'", 8, 9),
            TokenSpan("s", 9, 10),
        ]
        # Override includes the apostrophe
        overrides = [OverrideSpan(0, 10, {"ph": "nuː jɔːks", "lang": "en-us"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)
        assert len(result_tokens) == 1
        # All tokens in span should get the override
        assert result_tokens[0].meta["ph"] == "nuː jɔːks"
        assert all(t.lang == "en-us" for t in result_tokens)
        assert len(warnings) == 0

    def test_adjacent_punctuation_not_in_span(self):
        """Test that adjacent punctuation is NOT overridden if outside span."""
        tokens = [
            TokenSpan('"', 0, 1),
            TokenSpan("Hello", 1, 6),
            TokenSpan('"', 6, 7),
        ]
        # Override only the word, not the quotes
        overrides = [OverrideSpan(1, 6, {"ph": "hɛloʊ"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert "ph" not in result_tokens[0].meta  # First quote
        assert result_tokens[1].meta["ph"] == "hɛloʊ"  # Word
        assert "ph" not in result_tokens[2].meta  # Second quote
        assert len(warnings) == 0

    def test_multi_attribute_override(self):
        """Test override with multiple custom attributes."""
        tokens = [TokenSpan("test", 0, 4)]
        overrides = [
            OverrideSpan(
                0,
                4,
                {
                    "ph": "tɛst",
                    "lang": "en-us",
                    "rate": "slow",
                    "emphasis": "strong",
                    "volume": "loud",
                    "pitch": "+10Hz",
                },
            )
        ]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        # Check all attributes are applied
        assert result_tokens[0].meta["ph"] == "tɛst"
        assert result_tokens[0].lang == "en-us"
        assert result_tokens[0].meta["rate"] == "slow"
        assert result_tokens[0].meta["emphasis"] == "strong"
        assert result_tokens[0].meta["volume"] == "loud"
        assert result_tokens[0].meta["pitch"] == "+10Hz"
        assert result_tokens[0].meta["rating"] == 5
        assert len(warnings) == 0

    def test_overlapping_overrides_priority(self):
        """Test that later overrides take precedence for overlapping spans."""
        tokens = [
            TokenSpan("Hello", 0, 5),
            TokenSpan("world", 6, 11),
        ]
        overrides = [
            OverrideSpan(0, 11, {"ph": "first", "custom1": "A"}),
            OverrideSpan(6, 11, {"ph": "second", "custom2": "B"}),
        ]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        # First token gets first override only
        assert result_tokens[0].meta["ph"] == "second"
        assert result_tokens[0].meta["custom1"] == "A"
        # Second token gets BOTH overrides merged (later ph wins)
        assert len(warnings) == 1
        assert "override" in warnings[0].lower()

    def test_unicode_text_with_overrides(self):
        """Test overrides work correctly with Unicode text."""
        tokens = [
            TokenSpan("Café", 0, 4),
            TokenSpan("naïve", 5, 10),
            TokenSpan("résumé", 11, 17),
        ]
        overrides = [
            OverrideSpan(0, 4, {"ph": "kæˈfeɪ", "lang": "en-us"}),
            OverrideSpan(5, 10, {"ph": "naɪˈiv"}),
            OverrideSpan(11, 17, {"ph": "ˈɹɛzəˌmeɪ"}),
        ]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert result_tokens[0].meta["ph"] == "kæˈfeɪ"
        assert result_tokens[1].meta["ph"] == "naɪˈiv"
        assert result_tokens[2].meta["ph"] == "ˈɹɛzəˌmeɪ"
        assert len(warnings) == 0

    def test_whitespace_only_between_tokens(self):
        """Test that whitespace-only gaps don't affect override matching."""
        tokens = [
            TokenSpan("Hello", 0, 5),  # char 0-5
            TokenSpan("world", 7, 12),  # char 7-12 (gap at 5-7)
        ]
        # Override that spans the gap
        overrides = [OverrideSpan(0, 12, {"ph": "hɛloʊ wɝld"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)
        assert len(result_tokens) == 1
        # Both tokens should get the override despite the gap
        assert result_tokens[0].meta["ph"] == "hɛloʊ wɝld"
        assert len(warnings) == 0

    def test_zero_width_span_snaps(self):
        """Test that zero-width spans snap to containing token."""
        tokens = [TokenSpan("Hello", 0, 5)]
        overrides = [OverrideSpan(3, 3, {"ph": "test"})]  # Zero-width span

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        # Zero-width span within token snaps to that token
        assert result_tokens[0].meta["ph"] == "test"
        assert len(warnings) == 1
        assert "snapping" in warnings[0].lower()

    def test_duplicate_word_three_instances(self):
        """Test three instances of same word with different overrides."""
        tokens = [
            TokenSpan("read", 0, 4),  # Present tense: /ɹiːd/
            TokenSpan("I", 5, 6),
            TokenSpan("read", 7, 11),  # Past tense: /ɹɛd/
            TokenSpan("and", 12, 15),
            TokenSpan("read", 16, 20),  # Present tense: /ɹiːd/
        ]
        overrides = [
            OverrideSpan(0, 4, {"ph": "ɹiːd"}),  # First: present
            OverrideSpan(7, 11, {"ph": "ɹɛd"}),  # Second: past
            OverrideSpan(16, 20, {"ph": "ɹiːd"}),  # Third: present
        ]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        assert result_tokens[0].meta["ph"] == "ɹiːd"
        assert "ph" not in result_tokens[1].meta
        assert result_tokens[2].meta["ph"] == "ɹɛd"
        assert "ph" not in result_tokens[3].meta
        assert result_tokens[4].meta["ph"] == "ɹiːd"
        assert len(warnings) == 0

    def test_multi_token_phrase_override(self):
        """Test override spanning a complete multi-word phrase."""
        tokens = [
            TokenSpan("The", 0, 3),
            TokenSpan("United", 4, 10),
            TokenSpan("States", 11, 17),
            TokenSpan("of", 18, 20),
            TokenSpan("America", 21, 28),
        ]
        # Override for "United States of America"
        overrides = [OverrideSpan(4, 28, {"ph": "juːˌnaɪtɪd steɪts əv əˈmɛɹɪkə"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)
        assert len(result_tokens) == 2
        assert "ph" not in result_tokens[0].meta  # "The"
        # All tokens in phrase get same phonemes
        expected_ph = "juːˌnaɪtɪd steɪts əv əˈmɛɹɪkə"
        assert result_tokens[1].meta["ph"] == expected_ph
        assert len(warnings) == 0

    def test_partial_token_overlap_at_boundary(self):
        """Test override that ends exactly at token boundary."""
        tokens = [
            TokenSpan("Hello", 0, 5),
            TokenSpan("world", 6, 11),
            TokenSpan("!", 11, 12),
        ]
        # Override ends exactly where "world" ends
        overrides = [OverrideSpan(0, 11, {"ph": "hɛloʊ wɝld"})]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)
        assert len(result_tokens) == 2
        assert result_tokens[0].meta["ph"] == "hɛloʊ wɝld"
        assert "ph" not in result_tokens[1].meta  # Punctuation not included
        assert len(warnings) == 0

    def test_attribute_merging_different_keys(self):
        """Test that different attributes from multiple overrides are merged."""
        tokens = [TokenSpan("test", 0, 4)]
        overrides = [
            OverrideSpan(0, 4, {"ph": "tɛst"}),
            OverrideSpan(0, 4, {"lang": "en-us"}),
            OverrideSpan(0, 4, {"rate": "slow"}),
        ]

        result_tokens, warnings = apply_overrides_to_tokens(tokens, overrides)

        # All attributes should be present (last wins for duplicates)
        assert result_tokens[0].meta["ph"] == "tɛst"
        assert result_tokens[0].lang == "en-us"
        assert result_tokens[0].meta["rate"] == "slow"
        assert len(warnings) == 0
