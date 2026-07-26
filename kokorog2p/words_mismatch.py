"""Word count mismatch detection for G2P output.

This module detects when the number of words in input text doesn't match
the number of words in phonemized output. This is useful for:
1. Debugging phonemization issues
2. Quality control for TTS training data
3. Identifying problematic input text

Mismatches can occur when:
- Numbers expand (e.g., "5pm" → "five p m")
- Symbols expand (e.g., "$100" → "one hundred dollars")
- Contractions are handled differently
- Language-specific phonetic artifacts are inserted
"""

import abc
import logging
import re
from dataclasses import dataclass
from enum import Enum
from re import Pattern
from typing import Final

# =============================================================================
# Types and constants
# =============================================================================


class MismatchMode(Enum):
    """How to handle word count mismatches."""

    IGNORE = "ignore"  # Log summary only
    WARN = "warn"  # Log each mismatch with details
    REMOVE = "remove"  # Replace mismatched lines with empty string


@dataclass(frozen=True)
class MismatchInfo:
    """Information about a word count mismatch."""

    line_num: int  # 0-based line number
    expected: int  # Number of words in input
    actual: int  # Number of words in output
    input_text: str = ""  # Original input text (optional)
    output_text: str = ""  # Phonemized output (optional)

    def __str__(self) -> str:
        return (
            f"Line {self.line_num + 1}: "
            f"expected {self.expected} words, got {self.actual}"
        )


@dataclass
class MismatchStats:
    """Statistics about word count mismatches."""

    total_lines: int
    mismatched_lines: int
    mismatches: list[MismatchInfo]

    @property
    def mismatch_rate(self) -> float:
        """Percentage of lines with mismatches."""
        if self.total_lines == 0:
            return 0.0
        return (self.mismatched_lines / self.total_lines) * 100

    def __str__(self) -> str:
        return (
            f"Word count mismatches: {self.mismatched_lines}/{self.total_lines} "
            f"lines ({self.mismatch_rate:.1f}%)"
        )


# =============================================================================
# Word counting
# =============================================================================


# Default word separator pattern (whitespace)
_RE_WHITESPACE: Final[Pattern[str]] = re.compile(r"\s+")


def count_words(text: str, separator: str | Pattern[str] = _RE_WHITESPACE) -> int:
    """Count the number of words in text.

    Args:
        text: Text to count words in.
        separator: Word separator (string or regex pattern).

    Returns:
        Number of words.

    Examples:
        >>> count_words("hello world")
        2
        >>> count_words("hello  world")  # Multiple spaces
        2
        >>> count_words("")
        0
    """
    if not text or not text.strip():
        return 0

    if isinstance(separator, Pattern):
        words = [w for w in re.split(separator, text.strip()) if w]
    else:
        sep_pattern = re.compile(re.escape(separator))
        words = [w for w in re.split(sep_pattern, text.strip()) if w]

    return len(words)


def count_words_batch(
    texts: list[str], separator: str | Pattern[str] = _RE_WHITESPACE
) -> list[int]:
    """Count words in multiple texts.

    Args:
        texts: List of texts.
        separator: Word separator.

    Returns:
        List of word counts.
    """
    return [count_words(t, separator) for t in texts]


# =============================================================================
# Mismatch detection
# =============================================================================


def detect_mismatches(
    input_texts: list[str],
    output_texts: list[str],
    input_separator: str | Pattern[str] = _RE_WHITESPACE,
    output_separator: str | Pattern[str] = _RE_WHITESPACE,
    store_texts: bool = False,
) -> MismatchStats:
    """Detect word count mismatches between input and output.

    Args:
        input_texts: Original input texts.
        output_texts: Phonemized output texts.
        input_separator: Word separator for input.
        output_separator: Word separator for output.
        store_texts: Whether to store input/output in MismatchInfo.

    Returns:
        MismatchStats with details about any mismatches.

    Raises:
        ValueError: If input and output have different lengths.

    Examples:
        >>> inputs = ["hello world", "one two three"]
        >>> outputs = ["həˈloʊ wˈɜːld", "wˈʌn tuː θɹiː fɔːɹ"]  # Extra word!
        >>> stats = detect_mismatches(inputs, outputs)
        >>> stats.mismatched_lines
        1
        >>> stats.mismatches[0].line_num
        1
    """
    if len(input_texts) != len(output_texts):
        raise ValueError(
            f"Input and output must have same length: "
            f"{len(input_texts)} vs {len(output_texts)}"
        )

    input_counts = count_words_batch(input_texts, input_separator)
    output_counts = count_words_batch(output_texts, output_separator)

    mismatches: list[MismatchInfo] = []
    for i, (inp_count, out_count) in enumerate(
        zip(input_counts, output_counts, strict=False)
    ):
        if inp_count != out_count:
            mismatches.append(
                MismatchInfo(
                    line_num=i,
                    expected=inp_count,
                    actual=out_count,
                    input_text=input_texts[i] if store_texts else "",
                    output_text=output_texts[i] if store_texts else "",
                )
            )

    return MismatchStats(
        total_lines=len(input_texts),
        mismatched_lines=len(mismatches),
        mismatches=mismatches,
    )


# =============================================================================
# Mismatch processors
# =============================================================================


class BaseMismatchProcessor(abc.ABC):
    """Base class for word count mismatch processors."""

    def __init__(self, logger: logging.Logger | None = None):
        """Initialize processor.

        Args:
            logger: Logger instance. If None, uses module logger.
        """
        self._logger = logger or logging.getLogger(__name__)
        self._input_counts: list[int] = []
        self._output_counts: list[int] = []

    def count_input(
        self, texts: list[str], separator: str | Pattern[str] = _RE_WHITESPACE
    ) -> None:
        """Store word counts for input texts."""
        self._input_counts = count_words_batch(texts, separator)

    def count_output(
        self, texts: list[str], separator: str | Pattern[str] = _RE_WHITESPACE
    ) -> None:
        """Store word counts for output texts."""
        self._output_counts = count_words_batch(texts, separator)

    def _get_mismatches(self) -> list[tuple[int, int, int]]:
        """Get list of (line_num, expected, actual) for mismatches."""
        if len(self._input_counts) != len(self._output_counts):
            raise RuntimeError(
                f"Input and output counts differ in length: "
                f"{len(self._input_counts)} vs {len(self._output_counts)}"
            )

        return [
            (i, inp, out)
            for i, (inp, out) in enumerate(
                zip(self._input_counts, self._output_counts, strict=False)
            )
            if inp != out
        ]

    def _log_summary(self, num_mismatches: int, total: int) -> None:
        """Log a summary of mismatches."""
        if num_mismatches > 0:
            rate = round(num_mismatches / total * 100, 1) if total > 0 else 0
            self._logger.warning(
                "Word count mismatch on %.1f%% of lines (%d/%d)",
                rate,
                num_mismatches,
                total,
            )

    @abc.abstractmethod
    def process(self, texts: list[str]) -> list[str]:
        """Process texts based on detected mismatches.

        Args:
            texts: Output texts to process.

        Returns:
            Processed texts (may be modified based on mode).
        """
        raise NotImplementedError


class IgnoreMismatch(BaseMismatchProcessor):
    """Ignore mismatches, only log summary."""

    def process(self, texts: list[str]) -> list[str]:
        """Return texts unchanged, log summary."""
        mismatches = self._get_mismatches()
        self._log_summary(len(mismatches), len(texts))
        return texts


class WarnMismatch(BaseMismatchProcessor):
    """Warn about each mismatch with details."""

    def process(self, texts: list[str]) -> list[str]:
        """Return texts unchanged, log each mismatch."""
        mismatches = self._get_mismatches()

        for line_num, expected, actual in mismatches:
            self._logger.warning(
                "Word count mismatch on line %d: expected %d words, got %d",
                line_num + 1,
                expected,
                actual,
            )

        self._log_summary(len(mismatches), len(texts))
        return texts


class RemoveMismatch(BaseMismatchProcessor):
    """Remove lines with mismatches (replace with empty string)."""

    def process(self, texts: list[str]) -> list[str]:
        """Replace mismatched lines with empty strings."""
        mismatches = self._get_mismatches()
        mismatch_indices = {m[0] for m in mismatches}

        self._log_summary(len(mismatches), len(texts))
        if mismatches:
            self._logger.warning("Removing %d mismatched lines", len(mismatches))

        result = texts.copy()
        for idx in mismatch_indices:
            result[idx] = ""

        return result


def get_mismatch_processor(
    mode: MismatchMode | str, logger: logging.Logger | None = None
) -> BaseMismatchProcessor:
    """Get a mismatch processor for the given mode.

    Args:
        mode: Processing mode (ignore, warn, or remove).
        logger: Logger instance.

    Returns:
        Appropriate mismatch processor.

    Raises:
        ValueError: If mode is invalid.

    Examples:
        >>> processor = get_mismatch_processor("warn")
        >>> processor.count_input(["hello world"])
        >>> processor.count_output(["həˈloʊ wˈɜːld"])
        >>> result = processor.process(["həˈloʊ wˈɜːld"])
    """
    if isinstance(mode, str):
        try:
            mode = MismatchMode(mode.lower())
        except ValueError as e:
            valid = ", ".join(m.value for m in MismatchMode)
            raise ValueError(f"Invalid mode '{mode}', must be one of: {valid}") from e

    processors = {
        MismatchMode.IGNORE: IgnoreMismatch,
        MismatchMode.WARN: WarnMismatch,
        MismatchMode.REMOVE: RemoveMismatch,
    }

    return processors[mode](logger)


# =============================================================================
# Convenience function
# =============================================================================


def check_word_alignment(
    input_texts: list[str],
    output_texts: list[str],
    mode: MismatchMode | str = MismatchMode.WARN,
    input_separator: str | Pattern[str] = _RE_WHITESPACE,
    output_separator: str | Pattern[str] = _RE_WHITESPACE,
    logger: logging.Logger | None = None,
) -> tuple[list[str], MismatchStats]:
    """Check word alignment between input and output, optionally fixing issues.

    This is a convenience function that combines detection and processing.

    Args:
        input_texts: Original input texts.
        output_texts: Phonemized output texts.
        mode: How to handle mismatches (ignore, warn, remove).
        input_separator: Word separator for input texts.
        output_separator: Word separator for output texts.
        logger: Logger instance.

    Returns:
        Tuple of (processed_outputs, statistics).

    Examples:
        >>> inputs = ["hello world", "good morning"]
        >>> outputs = ["həˈloʊ wˈɜːld", "gʊd ˈmɔːnɪŋ ɛkstɹə"]
        >>> result, stats = check_word_alignment(inputs, outputs, mode="warn")
        >>> stats.mismatched_lines
        1
    """
    # Detect mismatches
    stats = detect_mismatches(
        input_texts,
        output_texts,
        input_separator,
        output_separator,
        store_texts=True,
    )

    # Process based on mode
    processor = get_mismatch_processor(mode, logger)
    processor.count_input(input_texts, input_separator)
    processor.count_output(output_texts, output_separator)
    processed = processor.process(output_texts)

    return processed, stats
