#!/usr/bin/env python3
"""Unit tests for benchmark validation logic.

Tests the validation rules used in benchmark_en_quotes_contractions.py
to ensure they correctly identify issues with G2P output.
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.benchmark_en_synthetic import QuotesContractionsBenchmark
from benchmarks.random_sentence_generator import TestCase


class TestValidationRules:
    """Test validation rules for quotes and contractions."""

    @pytest.fixture
    def benchmark(self):
        """Create benchmark instance for testing."""
        return QuotesContractionsBenchmark(num_tests=1, verbose=False)

    def test_contraction_with_acute_not_treated_as_quote(self, benchmark):
        """Contractions with acute (´) should not trigger quote validation."""
        # This is the bug case: "we´d" contains acute but it's a contraction,
        # not a quote
        test_case = TestCase(
            text="Gonna quick we´d world put.",
            category="apostrophe_variants",
            params={
                "apostrophe_type": "acute",
                "num_contractions": 2,
                "apostrophe_char": "´",
            },
        )
        # Expected output: contracted phonemes with acute normalized to apostrophe
        phonemes = "ɡˈʌnə kwˈɪk wid wˈɜɹld pˌʊt."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed, f"Should pass but got: {msg}"
        assert msg == "OK"

    def test_contraction_with_backtick_not_treated_as_quote(self, benchmark):
        """Contractions with backtick (`) should not trigger quote validation."""
        test_case = TestCase(
            text="I don`t know.",
            category="apostrophe_variants",
            params={"apostrophe_type": "backtick", "apostrophe_char": "`"},
        )
        phonemes = "ˈI dˈOnt nˈO."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed, f"Should pass but got: {msg}"

    def test_standalone_backtick_as_quote_requires_curly_quotes(self, benchmark):
        """Standalone backtick should be treated as quote and require curly output."""
        test_case = TestCase(
            text="She said `hello world`.",
            category="quote_variants",
            params={"quote_type": "backtick"},
        )
        # Missing curly quotes - should fail
        phonemes = "ʃˌi sˈɛd həlˈO wˈɜɹld."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert not passed
        assert "curly quotes" in msg.lower()

    def test_standalone_acute_as_quote_requires_curly_quotes(self, benchmark):
        """Standalone acute should be treated as quote and require curly output."""
        test_case = TestCase(
            text="She said ´hello world´.",
            category="quote_variants",
            params={"quote_type": "acute"},
        )
        # Missing curly quotes - should fail
        phonemes = "ʃˌi sˈɛd həlˈO wˈɜɹld."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert not passed
        assert "curly quotes" in msg.lower()

    def test_curly_quotes_in_output_passes(self, benchmark):
        """Output with curly quotes should pass validation."""
        test_case = TestCase(
            text='She said "hello world".',
            category="basic_quotes",
            params={"quote_type": "straight"},
        )
        # Has curly quotes (U+201C and U+201D)
        phonemes = "ʃˌi sˈɛd \u201chəlˈO wˈɜɹld\u201d."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"

    def test_straight_quotes_in_output_fails(self, benchmark):
        """Output with straight quotes should fail validation."""
        test_case = TestCase(
            text='She said "hello world".',
            category="basic_quotes",
            params={"quote_type": "straight"},
        )
        # Has straight quotes instead of curly
        phonemes = 'ʃˌi sˈɛd "həlˈO wˈɜɹld".'

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert not passed
        assert "straight quotes" in msg.lower()

    def test_guillemets_in_output_fails(self, benchmark):
        """Output with guillemets should fail validation."""
        test_case = TestCase(
            text="She said «hello world».",
            category="quote_variants",
            params={"quote_type": "guillemet"},
        )
        # Guillemets not converted
        phonemes = "ʃˌi sˈɛd «həlˈO wˈɜɹld»."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert not passed
        assert "guillemets" in msg.lower()

    def test_spelled_out_contraction_fails(self, benchmark):
        """Contractions spelled out letter-by-letter should fail."""
        test_case = TestCase(
            text="I don't know.",
            category="contractions",
            params={"apostrophe_type": "standard"},
        )
        # "don't" spelled as "d o n t" (wrong!)
        phonemes = "ˈI dˈi ˈO ˈɛn tˈi nˈO."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert not passed
        assert "spelled out" in msg.lower()

    def test_proper_contraction_passes(self, benchmark):
        """Properly handled contractions should pass."""
        test_case = TestCase(
            text="I don't know.",
            category="contractions",
            params={"apostrophe_type": "standard"},
        )
        # "don't" as single phoneme unit (correct!)
        phonemes = "ˈI dˈOnt nˈO."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"

    def test_nested_quotes_with_curly_passes(self, benchmark):
        """Nested quotes with curly quotes should pass."""
        test_case = TestCase(
            text='She said "he replied "yes" to me".',
            category="nested_quotes",
            params={"quote_type": "nested"},
        )
        # Nested curly quotes (correct pattern: L L R R)
        phonemes = "ʃˌi sˈɛd \u201chˌi ɹᵻplˈId \u201cjˈɛs\u201d tˌu mˈi\u201d."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"

    def test_no_quotes_in_text_passes_without_curly(self, benchmark):
        """Text without quotes should pass even without curly quotes in output."""
        test_case = TestCase(
            text="Hello world.",
            category="basic",
            params={},
        )
        phonemes = "həlˈO wˈɜɹld."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"

    def test_apostrophe_s_possessive_not_flagged(self, benchmark):
        """Possessive 's should not be flagged as contraction issue."""
        test_case = TestCase(
            text="John's book is here.",
            category="possessive",
            params={},
        )
        phonemes = "dʒˈɑnz bˈʊk ˈɪz hˈɪɹ."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"

    def test_multiple_contractions_in_sentence(self, benchmark):
        """Multiple contractions should all be handled correctly."""
        test_case = TestCase(
            text="I don't think we'll go.",
            category="contractions",
            params={"num_contractions": 2},
        )
        phonemes = "ˈI dˈOnt θˈɪŋk wˈil ɡˈO."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"

    def test_mixed_quotes_and_contractions(self, benchmark):
        """Mix of quotes and contractions should be handled correctly."""
        test_case = TestCase(
            text='She said "I don\'t know".',
            category="mixed",
            params={"has_quotes": True, "has_contractions": True},
        )
        phonemes = "ʃˌi sˈɛd \u201cˈI dˈOnt nˈO\u201d."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"


class TestEdgeCases:
    """Test edge cases in validation."""

    @pytest.fixture
    def benchmark(self):
        """Create benchmark instance for testing."""
        return QuotesContractionsBenchmark(num_tests=1, verbose=False)

    def test_backtick_at_start_of_text_as_quote(self, benchmark):
        """Backtick at start of text should be treated as quote."""
        test_case = TestCase(
            text="`Hello` she said.",
            category="quote_variants",
            params={"quote_type": "backtick"},
        )
        # No curly quotes - should fail
        phonemes = "həlˈO ʃˌi sˈɛd."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert not passed
        assert "curly quotes" in msg.lower()

    def test_acute_at_end_of_text_as_quote(self, benchmark):
        """Acute at end of text should be treated as quote."""
        test_case = TestCase(
            text="She said ´hello´",
            category="quote_variants",
            params={"quote_type": "acute"},
        )
        # No curly quotes - should fail
        phonemes = "ʃˌi sˈɛd həlˈO"

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert not passed
        assert "curly quotes" in msg.lower()

    def test_backtick_in_middle_of_word_as_contraction(self, benchmark):
        """Backtick in middle of word should be treated as contraction."""
        test_case = TestCase(
            text="don`t",
            category="apostrophe_variants",
            params={"apostrophe_type": "backtick"},
        )
        # Proper contraction handling
        phonemes = "dˈOnt"

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"

    def test_empty_quotes(self, benchmark):
        """Empty quotes should still require curly quotes."""
        test_case = TestCase(
            text='She said "".',
            category="edge_cases",
            params={"quote_type": "empty"},
        )
        # Should have curly quotes even if empty
        phonemes = "ʃˌi sˈɛd \u201c\u201d."

        passed, msg = benchmark.validate_output(test_case, phonemes)
        assert passed
        assert msg == "OK"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
