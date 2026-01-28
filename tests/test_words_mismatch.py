"""Tests for word count mismatch detection module.

Tests cover:
1. Word counting functions
2. Mismatch detection
3. Processor modes (ignore, warn, remove)
4. Edge cases
5. Integration with phonemization
"""

import logging
import re

import pytest

from kokorog2p.words_mismatch import (
    BaseMismatchProcessor,
    IgnoreMismatch,
    MismatchInfo,
    MismatchMode,
    MismatchStats,
    RemoveMismatch,
    WarnMismatch,
    check_word_alignment,
    count_words,
    count_words_batch,
    detect_mismatches,
    get_mismatch_processor,
)

# =============================================================================
# Test word counting
# =============================================================================


class TestCountWords:
    """Test word counting functions."""

    def test_count_simple(self):
        """Count words in simple text."""
        assert count_words("hello world") == 2

    def test_count_single_word(self):
        """Count single word."""
        assert count_words("hello") == 1

    def test_count_multiple_spaces(self):
        """Handle multiple spaces between words."""
        assert count_words("hello  world") == 2
        assert count_words("hello   world") == 2

    def test_count_leading_spaces(self):
        """Handle leading spaces."""
        assert count_words("  hello world") == 2

    def test_count_trailing_spaces(self):
        """Handle trailing spaces."""
        assert count_words("hello world  ") == 2

    def test_count_empty_string(self):
        """Handle empty string."""
        assert count_words("") == 0

    def test_count_whitespace_only(self):
        """Handle whitespace-only string."""
        assert count_words("   ") == 0
        assert count_words("\t\n") == 0

    def test_count_with_custom_separator(self):
        """Count with custom separator."""
        assert count_words("hello-world-test", separator="-") == 3

    def test_count_with_regex_separator(self):
        """Count with regex separator."""
        pattern = re.compile(r"[-_]")
        assert count_words("hello-world_test", separator=pattern) == 3

    def test_count_phonemes_with_space_separator(self):
        """Count phoneme words separated by space."""
        assert count_words("həˈloʊ wˈɜːld") == 2

    def test_count_many_words(self):
        """Count many words."""
        text = " ".join(["word"] * 100)
        assert count_words(text) == 100


class TestCountWordsBatch:
    """Test batch word counting."""

    def test_batch_simple(self):
        """Count words in batch."""
        texts = ["hello world", "one two three"]
        assert count_words_batch(texts) == [2, 3]

    def test_batch_empty_list(self):
        """Handle empty list."""
        assert count_words_batch([]) == []

    def test_batch_with_empty_strings(self):
        """Handle empty strings in batch."""
        texts = ["hello", "", "world"]
        assert count_words_batch(texts) == [1, 0, 1]

    def test_batch_with_custom_separator(self):
        """Batch with custom separator."""
        texts = ["a-b", "c-d-e"]
        assert count_words_batch(texts, separator="-") == [2, 3]


# =============================================================================
# Test MismatchInfo and MismatchStats
# =============================================================================


class TestMismatchInfo:
    """Test MismatchInfo dataclass."""

    def test_creation(self):
        """Create MismatchInfo."""
        info = MismatchInfo(line_num=0, expected=2, actual=3)
        assert info.line_num == 0
        assert info.expected == 2
        assert info.actual == 3

    def test_with_texts(self):
        """Create with input/output texts."""
        info = MismatchInfo(
            line_num=0,
            expected=2,
            actual=3,
            input_text="hello world",
            output_text="həˈloʊ wˈɜːld extra",
        )
        assert info.input_text == "hello world"
        assert info.output_text == "həˈloʊ wˈɜːld extra"

    def test_str_representation(self):
        """String representation."""
        info = MismatchInfo(line_num=0, expected=2, actual=3)
        s = str(info)
        assert "1" in s  # Line number (1-indexed)
        assert "2" in s  # Expected
        assert "3" in s  # Actual

    def test_frozen(self):
        """MismatchInfo should be frozen."""
        from dataclasses import FrozenInstanceError

        info = MismatchInfo(line_num=0, expected=2, actual=3)
        with pytest.raises(FrozenInstanceError):
            info.line_num = 1  # type: ignore[misc]


class TestMismatchStats:
    """Test MismatchStats dataclass."""

    def test_creation(self):
        """Create MismatchStats."""
        stats = MismatchStats(total_lines=10, mismatched_lines=2, mismatches=[])
        assert stats.total_lines == 10
        assert stats.mismatched_lines == 2

    def test_mismatch_rate(self):
        """Calculate mismatch rate."""
        stats = MismatchStats(total_lines=10, mismatched_lines=2, mismatches=[])
        assert stats.mismatch_rate == 20.0

    def test_mismatch_rate_zero_total(self):
        """Mismatch rate with zero total."""
        stats = MismatchStats(total_lines=0, mismatched_lines=0, mismatches=[])
        assert stats.mismatch_rate == 0.0

    def test_str_representation(self):
        """String representation."""
        stats = MismatchStats(total_lines=10, mismatched_lines=2, mismatches=[])
        s = str(stats)
        assert "2/10" in s
        assert "20" in s  # Percentage


# =============================================================================
# Test mismatch detection
# =============================================================================


class TestDetectMismatches:
    """Test mismatch detection."""

    def test_no_mismatches(self):
        """Detect no mismatches when aligned."""
        inputs = ["hello world", "good morning"]
        outputs = ["həˈloʊ wˈɜːld", "gʊd ˈmɔːnɪŋ"]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0
        assert stats.total_lines == 2

    def test_single_mismatch(self):
        """Detect single mismatch."""
        inputs = ["hello world"]
        outputs = ["həˈloʊ wˈɜːld extra"]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 1
        assert stats.mismatches[0].expected == 2
        assert stats.mismatches[0].actual == 3

    def test_multiple_mismatches(self):
        """Detect multiple mismatches."""
        inputs = ["one two", "one two three", "one"]
        outputs = ["wˈʌn tuː θriː", "wˈʌn tuː", "wˈʌn tuː"]  # All wrong!
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 3

    def test_with_store_texts(self):
        """Store input/output texts in MismatchInfo."""
        inputs = ["hello world"]
        outputs = ["həˈloʊ wˈɜːld extra"]
        stats = detect_mismatches(inputs, outputs, store_texts=True)
        assert stats.mismatches[0].input_text == "hello world"
        assert stats.mismatches[0].output_text == "həˈloʊ wˈɜːld extra"

    def test_different_lengths_error(self):
        """Error when input/output have different lengths."""
        inputs = ["hello", "world"]
        outputs = ["həˈloʊ"]
        with pytest.raises(ValueError, match="same length"):
            detect_mismatches(inputs, outputs)

    def test_custom_separators(self):
        """Use custom separators for counting."""
        inputs = ["hello-world"]
        outputs = ["həˈloʊ wˈɜːld"]
        stats = detect_mismatches(
            inputs,
            outputs,
            input_separator="-",
            output_separator=" ",
        )
        assert stats.mismatched_lines == 0  # Both have 2 "words"

    def test_empty_inputs(self):
        """Handle empty inputs."""
        stats = detect_mismatches([], [])
        assert stats.total_lines == 0
        assert stats.mismatched_lines == 0


# =============================================================================
# Test mismatch processors
# =============================================================================


class TestIgnoreMismatch:
    """Test IgnoreMismatch processor."""

    def test_process_returns_unchanged(self):
        """Process should return texts unchanged."""
        processor = IgnoreMismatch()
        processor._input_counts = [2, 3]
        processor._output_counts = [2, 4]  # Mismatch on second

        texts = ["həˈloʊ wˈɜːld", "wˈʌn tuː θɹiː fɔːɹ"]
        result = processor.process(texts)
        assert result == texts

    def test_logs_summary(self, caplog):
        """Should log summary."""
        processor = IgnoreMismatch()
        processor._input_counts = [2, 3]
        processor._output_counts = [2, 4]

        with caplog.at_level(logging.WARNING):
            processor.process(["a b", "c d e f"])

        assert "mismatch" in caplog.text.lower()


class TestWarnMismatch:
    """Test WarnMismatch processor."""

    def test_process_returns_unchanged(self):
        """Process should return texts unchanged."""
        processor = WarnMismatch()
        processor._input_counts = [2, 3]
        processor._output_counts = [2, 4]

        texts = ["a b", "c d e f"]
        result = processor.process(texts)
        assert result == texts

    def test_logs_each_mismatch(self, caplog):
        """Should log each mismatch."""
        processor = WarnMismatch()
        processor._input_counts = [2, 3]
        processor._output_counts = [3, 4]

        with caplog.at_level(logging.WARNING):
            processor.process(["a b c", "d e f g"])

        # Should have warnings for both lines
        assert "line 1" in caplog.text.lower()
        assert "line 2" in caplog.text.lower()


class TestRemoveMismatch:
    """Test RemoveMismatch processor."""

    def test_process_removes_mismatched(self):
        """Process should replace mismatched lines with empty string."""
        processor = RemoveMismatch()
        processor._input_counts = [2, 3, 2]
        processor._output_counts = [2, 4, 3]  # Lines 1 and 2 mismatch (0-indexed)

        texts = ["a b", "c d e f", "g h i"]
        result = processor.process(texts)
        assert result[0] == "a b"  # Unchanged
        assert result[1] == ""  # Removed
        assert result[2] == ""  # Removed

    def test_logs_removal(self, caplog):
        """Should log removal."""
        processor = RemoveMismatch()
        processor._input_counts = [2]
        processor._output_counts = [3]

        with caplog.at_level(logging.WARNING):
            processor.process(["a b c"])

        assert "removing" in caplog.text.lower()


# =============================================================================
# Test get_mismatch_processor factory
# =============================================================================


class TestGetMismatchProcessor:
    """Test processor factory function."""

    def test_get_ignore(self):
        """Get ignore processor."""
        processor = get_mismatch_processor(MismatchMode.IGNORE)
        assert isinstance(processor, IgnoreMismatch)

    def test_get_warn(self):
        """Get warn processor."""
        processor = get_mismatch_processor(MismatchMode.WARN)
        assert isinstance(processor, WarnMismatch)

    def test_get_remove(self):
        """Get remove processor."""
        processor = get_mismatch_processor(MismatchMode.REMOVE)
        assert isinstance(processor, RemoveMismatch)

    def test_get_by_string(self):
        """Get processor by string."""
        assert isinstance(get_mismatch_processor("ignore"), IgnoreMismatch)
        assert isinstance(get_mismatch_processor("warn"), WarnMismatch)
        assert isinstance(get_mismatch_processor("remove"), RemoveMismatch)

    def test_get_by_string_case_insensitive(self):
        """String mode should be case-insensitive."""
        assert isinstance(get_mismatch_processor("IGNORE"), IgnoreMismatch)
        assert isinstance(get_mismatch_processor("Warn"), WarnMismatch)

    def test_invalid_mode_error(self):
        """Invalid mode should raise error."""
        with pytest.raises(ValueError, match="Invalid mode"):
            get_mismatch_processor("invalid")

    def test_custom_logger(self):
        """Pass custom logger."""
        logger = logging.getLogger("test")
        processor = get_mismatch_processor("warn", logger=logger)
        assert processor._logger is logger


# =============================================================================
# Test check_word_alignment convenience function
# =============================================================================


class TestCheckWordAlignment:
    """Test check_word_alignment convenience function."""

    def test_aligned_texts(self):
        """Check aligned texts."""
        inputs = ["hello world", "good morning"]
        outputs = ["həˈloʊ wˈɜːld", "gʊd ˈmɔːnɪŋ"]
        result, stats = check_word_alignment(inputs, outputs)
        assert stats.mismatched_lines == 0
        assert result == outputs

    def test_misaligned_with_warn(self):
        """Check misaligned texts with warn mode."""
        inputs = ["hello world"]
        outputs = ["həˈloʊ wˈɜːld extra"]
        result, stats = check_word_alignment(inputs, outputs, mode="warn")
        assert stats.mismatched_lines == 1
        assert result == outputs  # Unchanged

    def test_misaligned_with_remove(self):
        """Check misaligned texts with remove mode."""
        inputs = ["hello world", "test"]
        outputs = ["həˈloʊ wˈɜːld extra", "tɛst"]
        result, stats = check_word_alignment(inputs, outputs, mode="remove")
        assert stats.mismatched_lines == 1
        assert result[0] == ""  # Removed
        assert result[1] == "tɛst"  # Unchanged

    def test_stores_texts_in_stats(self):
        """Stats should store input/output texts."""
        inputs = ["hello world"]
        outputs = ["həˈloʊ wˈɜːld extra"]
        _, stats = check_word_alignment(inputs, outputs)
        assert stats.mismatches[0].input_text == "hello world"


# =============================================================================
# Test edge cases
# =============================================================================


class TestMismatchEdgeCases:
    """Test edge cases for mismatch detection."""

    def test_single_empty_input(self):
        """Handle single empty input."""
        inputs = [""]
        outputs = [""]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0

    def test_mixed_empty_and_content(self):
        """Handle mix of empty and content."""
        inputs = ["hello world", "", "test"]
        outputs = ["həˈloʊ wˈɜːld", "", "tɛst"]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0

    def test_punctuation_affects_count(self):
        """Punctuation attached to words affects count."""
        inputs = ["hello, world!"]  # 2 words with punctuation
        outputs = ["həˈloʊ wˈɜːld"]  # 2 words
        stats = detect_mismatches(inputs, outputs)
        # Depends on how punctuation is attached
        assert stats.total_lines == 1

    def test_unicode_text(self):
        """Handle Unicode text."""
        inputs = ["你好 世界"]
        outputs = ["nǐhǎo shìjiè"]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0

    def test_very_long_text(self):
        """Handle very long text."""
        words = ["word"] * 1000
        inputs = [" ".join(words)]
        outputs = [" ".join(["wɜːd"] * 1000)]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0

    def test_newlines_in_text(self):
        """Handle newlines in text."""
        inputs = ["hello\nworld"]  # Newline acts as separator
        outputs = ["həˈloʊ wˈɜːld"]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0  # Both have 2 words

    def test_tabs_in_text(self):
        """Handle tabs in text."""
        inputs = ["hello\tworld"]
        outputs = ["həˈloʊ wˈɜːld"]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0


# =============================================================================
# Test MismatchMode enum
# =============================================================================


class TestMismatchMode:
    """Test MismatchMode enum."""

    def test_values(self):
        """Check enum values."""
        assert MismatchMode.IGNORE.value == "ignore"
        assert MismatchMode.WARN.value == "warn"
        assert MismatchMode.REMOVE.value == "remove"

    def test_all_modes_covered(self):
        """All modes should have processors."""
        for mode in MismatchMode:
            processor = get_mismatch_processor(mode)
            assert isinstance(processor, BaseMismatchProcessor)


# =============================================================================
# Integration tests
# =============================================================================


class TestMismatchIntegration:
    """Integration tests with real phonemization scenarios."""

    def test_number_expansion_mismatch(self):
        """Numbers may expand to more words."""
        # "5pm" might become "five p m" (3 words instead of 1)
        inputs = ["meeting at 5pm"]
        outputs = ["ˈmiːtɪŋ æt faɪv piː ɛm"]  # Expanded
        stats = detect_mismatches(inputs, outputs)
        # 3 words -> 5 words = mismatch
        assert stats.mismatched_lines == 1

    def test_contraction_handling(self):
        """Contractions may be handled differently."""
        # "don't" could become "do not" (2 words)
        inputs = ["I don't know"]  # 3 words
        outputs = ["aɪ doʊ nɑːt noʊ"]  # 4 words if expanded
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 1

    def test_symbol_expansion(self):
        """Symbols may expand."""
        # "$100" could become "one hundred dollars" (3 words)
        inputs = ["costs $100"]  # 2 words
        outputs = ["kɔsts wʌn ˈhʌndrəd ˈdɑləz"]  # 4 words
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 1

    def test_alignment_preserved_simple(self):
        """Simple sentences should align."""
        inputs = ["hello world", "good morning", "how are you"]
        outputs = ["həˈloʊ wˈɜːld", "gʊd ˈmɔːnɪŋ", "haʊ ɑːr juː"]
        stats = detect_mismatches(inputs, outputs)
        assert stats.mismatched_lines == 0

    def test_batch_processing_workflow(self):
        """Test typical batch processing workflow."""
        # Simulate batch G2P output
        inputs = [
            "Hello world",
            "How are you today",
            "I am fine thanks",
        ]
        outputs = [
            "həˈloʊ wˈɜːld",
            "haʊ ɑːr juː təˈdeɪ",
            "aɪ æm faɪn θæŋks",
        ]

        # Check alignment
        result, stats = check_word_alignment(inputs, outputs, mode="warn")

        # All should align
        assert stats.mismatched_lines == 0
        assert stats.mismatch_rate == 0.0
        assert result == outputs
