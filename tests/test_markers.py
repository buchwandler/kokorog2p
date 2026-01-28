"""Tests for marker-delimited helper functions."""

import pytest

from kokorog2p.markers import apply_marker_overrides, parse_delimited
from kokorog2p.types import OverrideSpan


class TestParseDelimited:
    """Tests for parse_delimited function."""

    def test_single_marker(self):
        """Test parsing single marked word."""
        text = "I like @coffee@."
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "I like coffee."
        assert ranges == [(7, 13)]  # "coffee"
        assert warnings == []

    def test_multiple_markers(self):
        """Test parsing multiple marked words."""
        text = "I like @coffee@ and @tea@."
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "I like coffee and tea."
        assert ranges == [(7, 13), (18, 21)]  # "coffee", "tea"
        assert warnings == []

    def test_no_markers(self):
        """Test text without markers."""
        text = "I like coffee."
        clean, ranges, warnings = parse_delimited(text)

        assert clean == text
        assert ranges == []
        assert warnings == []

    def test_escaped_marker(self):
        """Test escaped marker (literal @)."""
        text = r"Email: user\@example.com"
        clean, ranges, warnings = parse_delimited(text, marker="@", escape="\\")

        assert clean == "Email: user@example.com"
        assert ranges == []
        assert warnings == []

    def test_unmatched_opening_marker(self):
        """Test unmatched opening marker generates warning."""
        text = "Start @unmatched end"
        clean, ranges, warnings = parse_delimited(text)

        # Implementation keeps the marker as literal and emits a warning
        assert clean == "Start @unmatched end"
        assert ranges == []
        assert len(warnings) == 1
        assert "Unmatched opening marker" in warnings[0]

    def test_unmatched_closing_marker(self):
        """Test lone closing marker is removed like opening marker."""
        text = "Start word@ end"
        clean, ranges, warnings = parse_delimited(text)

        # Implementation keeps the marker as literal (treats as opening then unmatched)
        assert clean == "Start word@ end"
        assert ranges == []
        # Should get an unmatched warning
        assert len(warnings) == 1

    def test_nested_markers(self):
        """Test apparent nesting emits warning."""
        text = "@outer @inner@ outer@"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "outer inner outer"
        assert len(ranges) == 2
        assert any("nested" in warning.lower() for warning in warnings)

    def test_custom_marker(self):
        """Test using custom marker character."""
        text = "I like #coffee#."
        clean, ranges, warnings = parse_delimited(text, marker="#")

        assert clean == "I like coffee."
        assert ranges == [(7, 13)]
        assert warnings == []

    def test_custom_escape(self):
        """Test using custom escape character."""
        text = "Price: 5|$ total"
        clean, ranges, warnings = parse_delimited(text, marker="$", escape="|")

        assert clean == "Price: 5$ total"
        assert ranges == []
        assert warnings == []

    def test_multi_word_marker(self):
        """Test marking multi-word span."""
        text = "I visited @New York City@ last year."
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "I visited New York City last year."
        assert ranges == [(10, 23)]  # "New York City"
        assert warnings == []

    def test_adjacent_markers(self):
        """Test adjacent marked words."""
        text = "@Hello@ @World@"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "Hello World"
        assert ranges == [(0, 5), (6, 11)]
        assert warnings == []

    def test_empty_marker(self):
        """Test empty marked span."""
        text = "test @@word"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "test word"
        assert ranges == [(5, 5)]  # Empty range
        assert warnings == []

    def test_marker_at_start(self):
        """Test marker at text start."""
        text = "@Start@ middle end"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "Start middle end"
        assert ranges == [(0, 5)]
        assert warnings == []

    def test_marker_at_end(self):
        """Test marker at text end."""
        text = "start middle @End@"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "start middle End"
        assert ranges == [(13, 16)]
        assert warnings == []

    def test_duplicate_words_with_markers(self):
        """Test marking duplicate words distinctly."""
        text = "@the@ cat @the@ dog"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "the cat the dog"
        assert ranges == [(0, 3), (8, 11)]  # Both "the" instances
        assert warnings == []

    def test_punctuation_adjacent_markers(self):
        """Test markers adjacent to punctuation."""
        text = "Hello @world@! How are @you@?"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "Hello world! How are you?"
        assert ranges == [(6, 11), (21, 24)]
        assert warnings == []


class TestApplyMarkerOverrides:
    """Tests for apply_marker_overrides function."""

    def test_dict_assignment(self):
        """Test dict-based assignments (1-indexed)."""
        clean_text = "I like coffee and tea"
        ranges = [(7, 13), (18, 21)]  # "coffee", "tea"

        assignments = {1: {"ph": "ˈkɔfi"}, 2: {"ph": "tiː"}}

        overrides = apply_marker_overrides(clean_text, ranges, assignments)

        assert len(overrides) == 2
        assert isinstance(overrides[0], OverrideSpan)
        assert overrides[0].char_start == 7
        assert overrides[0].char_end == 13
        assert overrides[0].attrs == {"ph": "ˈkɔfi"}
        assert overrides[1].char_start == 18
        assert overrides[1].char_end == 21
        assert overrides[1].attrs == {"ph": "tiː"}

    def test_list_assignment(self):
        """Test list-based assignments (in order)."""
        clean_text = "I like coffee and tea"
        ranges = [(7, 13), (18, 21)]

        assignments = [{"ph": "ˈkɔfi"}, {"ph": "tiː"}]

        overrides = apply_marker_overrides(clean_text, ranges, assignments)

        assert len(overrides) == 2
        assert overrides[0].attrs == {"ph": "ˈkɔfi"}
        assert overrides[1].attrs == {"ph": "tiː"}

    def test_selective_dict_assignment(self):
        """Test selective assignment (skip markers)."""
        clean_text = "I like coffee and tea and water"
        ranges = [(7, 13), (18, 21), (26, 31)]

        # Only assign to markers 1 and 3
        assignments = {1: {"ph": "ˈkɔfi"}, 3: {"lang": "en-us"}}

        overrides = apply_marker_overrides(clean_text, ranges, assignments)

        # Should only get 2 overrides (marker 2 skipped)
        assert len(overrides) == 2
        assert overrides[0].char_start == 7
        assert overrides[0].attrs == {"ph": "ˈkɔfi"}
        assert overrides[1].char_start == 26
        assert overrides[1].attrs == {"lang": "en-us"}

    def test_language_override(self):
        """Test language switching."""
        clean_text = "Hello Bonjour world"
        ranges = [(6, 13)]  # "Bonjour"

        assignments = {1: {"lang": "fr"}}
        overrides = apply_marker_overrides(clean_text, ranges, assignments)

        assert len(overrides) == 1
        assert overrides[0].attrs == {"lang": "fr"}

    def test_combined_attributes(self):
        """Test multiple attributes in one override."""
        clean_text = "Hello world"
        ranges = [(0, 5)]

        assignments = {1: {"ph": "həlˈO", "speaker": "male", "emphasis": "strong"}}

        overrides = apply_marker_overrides(clean_text, ranges, assignments)

        assert len(overrides) == 1
        assert overrides[0].attrs["ph"] == "həlˈO"
        assert overrides[0].attrs["speaker"] == "male"
        assert overrides[0].attrs["emphasis"] == "strong"

    def test_empty_ranges(self):
        """Test with no ranges."""
        clean_text = "Hello world"
        ranges: list[tuple[int, int]] = []
        assignments: dict[int, dict[str, str]] = {}

        overrides = apply_marker_overrides(clean_text, ranges, assignments)

        assert overrides == []

    def test_list_assignment_length_mismatch(self):
        """Test list assignment with wrong count raises ValueError."""
        clean_text = "I like coffee and tea"
        ranges: list[tuple[int, int]] = [(7, 13), (18, 21)]

        # Only one assignment but two ranges - should raise
        assignments: list[dict[str, str]] = [{"ph": "ˈkɔfi"}]

        with pytest.raises(ValueError, match="does not match"):
            apply_marker_overrides(clean_text, ranges, assignments)

    def test_zero_indexed_dict_raises(self):
        """Test that 0-indexed dict keys raise ValueError (must be 1-indexed)."""
        clean_text = "I like coffee"
        ranges = [(7, 13)]

        # Using 0-index (invalid - should raise)
        assignments = {0: {"ph": "test"}}

        with pytest.raises(ValueError, match="out of range"):
            apply_marker_overrides(clean_text, ranges, assignments)

    def test_duplicate_word_overrides(self):
        """Test overriding duplicate words differently."""
        clean_text = "the cat the dog"
        ranges = [(0, 3), (8, 11)]

        assignments = {1: {"ph": "ðə"}, 2: {"ph": "ði"}}

        overrides = apply_marker_overrides(clean_text, ranges, assignments)

        assert len(overrides) == 2
        assert overrides[0].char_start == 0
        assert overrides[0].char_end == 3
        assert overrides[0].attrs["ph"] == "ðə"
        assert overrides[1].char_start == 8
        assert overrides[1].char_end == 11
        assert overrides[1].attrs["ph"] == "ði"


class TestIntegration:
    """Integration tests with phonemize_to_result."""

    def test_basic_integration(self):
        """Test full workflow from markers to phonemization."""
        from kokorog2p import phonemize_to_result

        text = "I like @coffee@."
        clean, ranges, warnings = parse_delimited(text)

        assignments = {1: {"ph": "ˈkɔfi"}}
        overrides = apply_marker_overrides(clean, ranges, assignments)

        result = phonemize_to_result(clean, lang="en-us", overrides=overrides)

        # Should have phonemized successfully
        assert result.phonemes is not None
        assert "ˈkɔfi" in result.phonemes
        assert len(result.warnings) == 0

    def test_duplicate_word_integration(self):
        """Test duplicate words with different phonemes."""
        from kokorog2p import phonemize_to_result

        text = "@the@ cat @the@ dog"
        clean, ranges, _ = parse_delimited(text)

        assignments = {1: {"ph": "ðə"}, 2: {"ph": "ði"}}
        overrides = apply_marker_overrides(clean, ranges, assignments)

        result = phonemize_to_result(clean, lang="en-us", overrides=overrides)

        # Both "the" instances should be in the result
        assert result.phonemes is not None
        assert "ðə" in result.phonemes
        assert "ði" in result.phonemes

    def test_language_switch_integration(self):
        """Test language switching."""
        from kokorog2p import phonemize_to_result

        text = "Hello @Bonjour@ world"
        clean, ranges, _ = parse_delimited(text)

        assignments = {1: {"lang": "fr"}}
        overrides = apply_marker_overrides(clean, ranges, assignments)

        result = phonemize_to_result(clean, lang="en-us", overrides=overrides)

        # Should have phonemized successfully with language switch
        assert result.phonemes is not None
        # French word should be processed with French G2P
        french_tokens = [t for t in result.tokens if t.lang == "fr"]
        assert len(french_tokens) > 0


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_marker_with_unicode(self):
        """Test markers with unicode text."""
        text = "Das ist @schön@."
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "Das ist schön."
        assert ranges == [(8, 13)]
        assert warnings == []

    def test_marker_preserves_spacing(self):
        """Test that spacing is preserved correctly."""
        text = "@word1@  @word2@"  # Two spaces between
        clean, ranges, warnings = parse_delimited(text)

        assert clean == "word1  word2"  # Two spaces preserved
        assert ranges == [(0, 5), (7, 12)]

    def test_multiple_escapes(self):
        """Test multiple escaped markers."""
        text = r"user\@example.com and admin\@test.org"
        clean, ranges, warnings = parse_delimited(text, marker="@", escape="\\")

        assert clean == "user@example.com and admin@test.org"
        assert ranges == []

    def test_empty_text(self):
        """Test empty input text."""
        text = ""
        clean, ranges, warnings = parse_delimited(text)

        assert clean == ""
        assert ranges == []
        assert warnings == []

    def test_only_markers(self):
        """Test text that is only markers."""
        text = "@@"
        clean, ranges, warnings = parse_delimited(text)

        assert clean == ""
        assert ranges == [(0, 0)]
        assert warnings == []
