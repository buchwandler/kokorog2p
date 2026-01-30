"""Tests for phoneme output spacing and formatting.

This module tests that phoneme outputs have correct spacing (matching misaki's behavior)
and that the benchmark wrapper correctly handles both marker output and clean output.
"""

import sys
from pathlib import Path

import pytest

from kokorog2p import phonemize
from kokorog2p.en.g2p import EnglishG2P


class TestPhonemeSpacing:
    """Test that phoneme output has correct spacing."""

    @pytest.fixture
    def g2p(self):
        """Create G2P instance for testing."""
        return EnglishG2P(use_espeak_fallback=True, use_spacy=False)

    @pytest.fixture(params=["english_g2p", "pipeline"])
    def phonemizer(self, request, g2p):
        """Provide phonemizer outputs for G2P and pipeline API."""
        if request.param == "english_g2p":
            return g2p.phonemize

        return lambda text: phonemize(text, g2p=g2p).phonemes or ""

    def test_double_quotes_no_extra_spaces(self, phonemizer):
        """Double quotes should not have extra spaces around them."""
        text = 'She said "hello".'
        result = phonemizer(text)

        # Should NOT have spaces like: ʃˌi sˈɛd " həlˈO " .
        # Should have: ʃˌi sˈɛd "həlˈO". (with curly quotes U+201C and U+201D)
        assert '" həlˈO "' not in result, "Should not have spaces around quoted word"
        assert "\u201c" in result and "\u201d" in result, "Should contain curly quotes"
        assert (
            "\u201chəlˈO\u201d" in result
        ), "Should have curly quotes directly around word"

    def test_period_no_extra_space_before(self, phonemizer):
        """Period should not have extra space before it."""
        text = "Hello world."
        result = phonemizer(text)

        # Should NOT end with: wˈɜɹld .
        # Should end with: wˈɜɹld.
        assert not result.endswith(" ."), "Period should not have space before it"
        assert result.endswith("."), "Should end with period"

    def test_comma_spacing(self, phonemizer):
        """Comma should follow natural spacing."""
        text = "Hello, world."
        result = phonemizer(text)

        # Should be: həlˈO,wˈɜɹld.
        # Should NOT be: həlˈO , wˈɜɹld .
        assert "," in result, "Comma should be followed by space"
        assert " ," not in result, "Comma should not have space before it"
        assert ", " not in result, "Comma should not have space before it"

    def test_whitespace_normalization(self, phonemizer, g2p):
        """Whitespace handling should match EnglishG2P output."""
        text = "Hello  world."  # Double space
        result = phonemizer(text)

        assert result == g2p.phonemize(text)

    def test_guillemets_converted_to_quotes(self, phonemizer):
        """Guillemets should be normalized to double quotes."""
        text = "Test «word» here."
        result = phonemizer(text)

        # Should contain curly quotes (U+201C and U+201D), not guillemets
        assert "\u201c" in result or "\u201d" in result, "Should contain curly quotes"
        assert "«" not in result, "Should not contain left guillemet"
        assert "»" not in result, "Should not contain right guillemet"
        assert "\u201cwˈɜɹd\u201d" in result, "Should have curly quotes around word"

    def test_single_guillemets_converted(self, phonemizer):
        """Single guillemets (‹›) should be normalized to double quotes."""
        text = "Test ‹word› here."
        result = phonemizer(text)

        # Should contain curly quotes (U+201C and U+201D)
        assert "\u201c" in result or "\u201d" in result, "Should contain curly quotes"
        assert "‹" not in result, "Should not contain single left guillemet"
        assert "›" not in result, "Should not contain single right guillemet"

    def test_ellipses(self, phonemizer):
        """Ellispes"""
        text = "Test . . . here."
        result = phonemizer(text)

        assert "…" in result, "Should contain ellipses"


class TestBenchmarkWrapperSpacing:
    """Test the benchmark wrapper specifically."""

    @pytest.fixture
    def wrapper(self):
        """Create benchmark wrapper."""
        # Add benchmarks directory to path
        benchmark_path = Path(__file__).parent.parent / "benchmarks"
        if str(benchmark_path) not in sys.path:
            sys.path.insert(0, str(benchmark_path))

        from benchmark_en_misaki import KokoroG2PWrapper

        return KokoroG2PWrapper("en-us")

    def test_phonemize_returns_tuple(self, wrapper):
        """phonemize() should return (phonemes, tokens)."""
        result = wrapper.phonemize("Hello world.")
        assert isinstance(result, tuple), "Should return tuple"
        assert len(result) == 2, "Should return (phonemes, tokens)"
        assert isinstance(result[0], str), "First element should be string"
        assert isinstance(result[1], list), "Second element should be list"

    def test_phonemize_clean_returns_string(self, wrapper):
        """phonemize_clean() should return string."""
        result = wrapper.phonemize_clean("Hello world.")
        assert isinstance(result, str), "Should return string"

    def test_no_extra_spaces_in_clean(self, wrapper):
        """Clean output should not have extra spaces around punctuation."""
        text = 'She said "hello world".'
        clean = wrapper.phonemize_clean(text)

        # Should not have spaces like: " hello world " .
        assert '" həlˈO wˈɜɹld "' not in clean, "Should not have extra spaces"
        assert not clean.endswith(" ."), "Should not have space before period"

    def test_no_extra_spaces_in_markers(self, wrapper):
        """Marker output should not have extra spaces around punctuation."""
        text = 'She said "hello world".'
        with_markers, _ = wrapper.phonemize(text)

        # Should not have spaces like: " hello world " .
        assert '" həlˈO wˈɜɹld "' not in with_markers, "Should not have extra spaces"
        assert not with_markers.endswith(" ."), "Should not have space before period"

    def test_single_quotes_filtered_in_clean(self, wrapper):
        """Single quotes (❓) should be filtered in clean output."""
        text = "Test 'word' here."

        with_markers, _ = wrapper.phonemize(text)
        clean = wrapper.phonemize_clean(text)

        # Markers may contain ❓
        # Clean should not
        assert "❓" not in clean, "Clean output should not contain quote markers"
        assert "wˈɜɹd" in clean, "Word should still be present"

    def test_guillemets_converted_to_quotes_both_outputs(self, wrapper):
        """Guillemets should be converted to " in both marker and clean output."""
        text = "Test «word» here."

        with_markers, _ = wrapper.phonemize(text)
        clean = wrapper.phonemize_clean(text)

        # Both should have curly quotes (U+201C and U+201D), not guillemets or markers
        assert (
            "\u201cwˈɜɹd\u201d" in with_markers
        ), "Markers should have curly quotes around word"
        assert (
            "\u201cwˈɜɹd\u201d" in clean
        ), "Clean should have curly quotes around word"

        # Should not have markers like [«] or [»]
        assert "[«]" not in with_markers, "Should not have guillemet markers"
        assert "[»]" not in with_markers, "Should not have guillemet markers"

        # Should not have actual guillemets
        assert "«" not in with_markers, "Should not have left guillemet"
        assert "»" not in with_markers, "Should not have right guillemet"
        assert "«" not in clean, "Should not have left guillemet"
        assert "»" not in clean, "Should not have right guillemet"

    def test_spacing_consistency_between_outputs(self, wrapper):
        """Both marker and clean outputs should have consistent spacing."""
        text = 'She said "hello".'

        with_markers, _ = wrapper.phonemize(text)
        clean = wrapper.phonemize_clean(text)

        # Extract spacing patterns
        # Both should have same spacing around punctuation
        for punct in ['"', ".", ","]:
            if punct in text:
                # Check space before
                assert (f" {punct}" in with_markers) == (
                    f" {punct}" in clean
                ), f"Space before '{punct}' should be consistent"

                # Check space after
                assert (f"{punct} " in with_markers) == (
                    f"{punct} " in clean
                ), f"Space after '{punct}' should be consistent"

    def test_multiple_quote_types(self, wrapper):
        """Test various quote types are all normalized to double quotes."""
        test_cases = [
            ('Test "word" here.', "Standard quotes"),
            ("Test «word» here.", "Guillemets"),
            ("Test ‹word› here.", "Single guillemets"),
            ('Test "word" here.', "Curly quotes"),
            ("Test ″word″ here.", "Double prime"),
            ("Test ＂word＂ here.", "Fullwidth quotes"),
        ]

        for text, desc in test_cases:
            clean = wrapper.phonemize_clean(text)

            # All should result in curly quotes (U+201C and U+201D)
            assert (
                "\u201c" in clean or "\u201d" in clean
            ), f"{desc} should result in curly quotes"
            assert (
                "\u201cwˈɜɹd\u201d" in clean or "\u201cwɜɹd\u201d" in clean
            ), f"{desc} should have curly quotes directly around word"

    def test_no_trailing_spaces(self, wrapper):
        """Output should not have trailing spaces."""
        texts = [
            "Hello world.",
            'She said "hello".',
            "Test «word» here.",
        ]

        for text in texts:
            with_markers, _ = wrapper.phonemize(text)
            clean = wrapper.phonemize_clean(text)

            assert not with_markers.endswith(
                " "
            ), f"Markers should not end with space: {repr(text)}"
            assert not clean.endswith(
                " "
            ), f"Clean should not end with space: {repr(text)}"

    def test_no_leading_spaces(self, wrapper):
        """Output should not have leading spaces."""
        texts = [
            "Hello world.",
            'She said "hello".',
            "Test «word» here.",
        ]

        for text in texts:
            with_markers, _ = wrapper.phonemize(text)
            clean = wrapper.phonemize_clean(text)

            assert not with_markers.startswith(
                " "
            ), f"Markers should not start with space: {repr(text)}"
            assert not clean.startswith(
                " "
            ), f"Clean should not start with space: {repr(text)}"
