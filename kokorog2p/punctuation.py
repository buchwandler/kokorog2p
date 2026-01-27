"""Punctuation handling for Kokoro TTS.

This module provides robust punctuation processing that:
1. Uses only punctuation marks supported by Kokoro's vocabulary
2. Handles edge cases like multiple punctuation, quotes, ellipses
3. Normalizes Unicode punctuation to ASCII equivalents
4. Preserves punctuation positions during phonemization

The Kokoro vocabulary supports these punctuation marks:
    ; : , . ! ? — … " ( ) " "

All other punctuation is either normalized or removed.
"""

import re
from dataclasses import dataclass
from enum import Enum
from re import Pattern
from typing import ClassVar, Final

# =============================================================================
# Kokoro-supported punctuation
# =============================================================================

# Punctuation marks in Kokoro's vocabulary (from kokoro_config.json)
# These are: ; : , . ! ? — … " ( ) " "
KOKORO_PUNCTUATION: Final[frozenset[str]] = frozenset(
    [
        ";",
        ":",
        ",",
        ".",
        "!",
        "?",
        "\u2014",  # — em-dash
        "\u2026",  # … ellipsis
        '"',  # straight double quote
        "(",
        ")",
        "\u201c",  # " left curly quote
        "\u201d",  # " right curly quote
    ]
)

# Default marks for preserve/restore operations
DEFAULT_MARKS: Final[str] = ';:,.!?—…"()\u201c\u201d'

# =============================================================================
# Unicode normalization mappings
# =============================================================================

# Map various Unicode punctuation to Kokoro-compatible equivalents
PUNCTUATION_NORMALIZATION: Final[dict[str, str]] = {
    # Apostrophes → ASCII apostrophe (for contractions)
    "\u2019": "'",  # ' right single quotation mark (most common)
    "\u2018": "'",  # ' left single quotation mark
    "`": "'",  # ` grave accent (common typo)
    "\u00b4": "'",  # ´ acute accent (common typo)
    "\u02b9": "'",  # ʹ modifier letter prime
    "\u2032": "'",  # ′ prime (mathematical)
    "\uff07": "'",  # ＇ fullwidth apostrophe
    # Dashes and hyphens → em-dash
    "\u2013": "—",  # – en-dash
    "\u2212": "—",  # − minus sign
    "\u2015": "—",  # ― horizontal bar
    "\u2012": "—",  # ‒ figure dash
    "\u2e3a": "—",  # ⸺ two-em dash
    "\u2e3b": "—",  # ⸻ three-em dash
    # Note: Single hyphen (-) and double hyphen (--) are handled in normalize()
    # Ellipsis variations → ellipsis character
    # Note: Multi-char sequences (..., .., ...., . . .) handled in normalize()
    "．．．": "…",  # fullwidth
    "・・・": "…",  # Japanese
    # Quotes → curly quotes (keep as-is) or normalize exotic ones to double quote
    "‚": '"',  # single low-9 quote
    "‛": '"',  # single high-reversed-9 quote
    "„": '"',  # double low-9 quote
    "‟": '"',  # double high-reversed-9 quote
    "«": '"',  # left guillemet
    "»": '"',  # right guillemet
    "‹": '"',  # single left guillemet
    "›": '"',  # single right guillemet
    "「": '"',  # Japanese left corner bracket
    "」": '"',  # Japanese right corner bracket
    "『": '"',  # Japanese left white corner bracket
    "』": '"',  # Japanese right white corner bracket
    "《": '"',  # Chinese left double angle bracket
    "》": '"',  # Chinese right double angle bracket
    # Colons and semicolons
    "；": ";",  # fullwidth semicolon
    "：": ":",  # fullwidth colon
    "︰": ":",  # presentation form
    # Commas
    "，": ",",  # fullwidth comma
    "、": ",",  # ideographic comma
    # Periods
    "．": ".",  # fullwidth period
    "。": ".",  # ideographic period
    "｡": ".",  # halfwidth ideographic period
    # Exclamation and question marks
    "！": "!",  # fullwidth exclamation
    "？": "?",  # fullwidth question mark
    "¡": "!",  # inverted exclamation (Spanish)
    "¿": "?",  # inverted question mark (Spanish)
    "⁉": "?",  # exclamation question mark
    "⁈": "!",  # question exclamation mark
    "‼": "!",  # double exclamation
    "⸮": "?",  # reversed question mark
    # Parentheses and brackets
    "［": "(",  # fullwidth left bracket
    "］": ")",  # fullwidth right bracket
    "【": "(",  # left black lenticular bracket
    "】": ")",  # right black lenticular bracket
    "〔": "(",  # left tortoise shell bracket
    "〕": ")",  # right tortoise shell bracket
    "〈": "(",  # left angle bracket
    "〉": ")",  # right angle bracket
    "｛": "(",  # fullwidth left curly bracket
    "｝": ")",  # fullwidth right curly bracket
    "（": "(",  # fullwidth left parenthesis
    "）": ")",  # fullwidth right parenthesis
    "[": "(",  # left square bracket
    "]": ")",  # right square bracket
    "{": "(",  # left curly bracket
    "}": ")",  # right curly bracket
}

# Characters to remove entirely (not normalizable to Kokoro vocab)
REMOVE_PUNCTUATION: Final[frozenset[str]] = frozenset(
    "~`@#$%^&*_+=\\|/<>"
    "～＠＃＄％＾＆＊＿＋＝｜＜＞"  # fullwidth versions
    "†‡§¶•·°±×÷©®™"  # symbols
    "→←↑↓↔↕"  # arrows (except Kokoro's pitch markers)
)


# =============================================================================
# Position tracking for preserve/restore
# =============================================================================


class Position(Enum):
    """Position of punctuation mark in utterance."""

    BEGIN = "B"  # At the beginning: "Hello
    END = "E"  # At the end: Hello!
    MIDDLE = "I"  # In the middle: Hello, world
    ALONE = "A"  # Entire utterance is punctuation: ...


@dataclass(frozen=True)
class MarkIndex:
    """Tracks a punctuation mark's original position."""

    index: int  # Line/utterance number
    mark: str  # The punctuation mark(s)
    position: Position  # Where in the utterance


# =============================================================================
# Punctuation class
# =============================================================================


class Punctuation:
    """Preserve, remove, or normalize punctuation during phonemization.

    This class provides methods to:
    1. Normalize Unicode punctuation to Kokoro-compatible marks
    2. remove configured marks
    3. Preserve punctuation positions for later restoration

    Examples:
        >>> punct = Punctuation()

        # Normalize Unicode punctuation
        >>> punct.normalize("Hello… world！")
        'Hello… world!'

        # Remove all punctuation
        >>> punct.remove("Hello, world!")
        'Hello world'

        # Preserve and restore
        >>> text, marks = punct.preserve("Hello, world!")
        >>> text
        ['Hello', 'world']
        >>> # After phonemization...
        >>> punct.restore(['həˈloʊ', 'wˈɜːld'], marks)
        ['həˈloʊ, wˈɜːld!']
    """

    def __init__(self, marks: str | Pattern = DEFAULT_MARKS):
        """Initialize punctuation handler.

        Args:
            marks: Punctuation marks to consider. Either a string of
                   single-character marks or a compiled regex pattern.
        """
        self._marks: str | None = None
        self._marks_re: Pattern[str] | None = None
        self.marks = marks

    @staticmethod
    def default_marks() -> str:
        """Return the default punctuation marks."""
        return DEFAULT_MARKS

    @staticmethod
    def kokoro_marks() -> frozenset[str]:
        """Return all punctuation marks in Kokoro's vocabulary."""
        return KOKORO_PUNCTUATION

    @property
    def marks(self) -> str:
        """The punctuation marks as a string."""
        if self._marks is not None:
            return self._marks
        raise ValueError(
            "Punctuation initialized from regex, cannot access marks as string"
        )

    @marks.setter
    def marks(self, value: str | Pattern) -> None:
        """Set the punctuation marks."""
        if isinstance(value, Pattern):
            # Wrap pattern to catch surrounding spaces
            self._marks_re = re.compile(rf"\s*(?:{value.pattern})\s*", value.flags)
            self._marks = None
        elif isinstance(value, str):
            self._marks = "".join(dict.fromkeys(value))
            # Build regex: zero or more spaces + one or more marks + zero or more spaces
            escaped = re.escape(self._marks)
            self._marks_re = re.compile(rf"(\s*[{escaped}]+\s*)+")
        else:
            raise ValueError("Punctuation marks must be a string or re.Pattern")

    # One-pass matcher for multi-character sequences (order handled by regex engine).
    _SEQ_RE: ClassVar[re.Pattern[str]] = re.compile(
        # Allow variable whitespace (spaces/tabs/newlines)
        # around/between dots and hyphens.
        # This makes normalization robust to inputs like
        # ".  . .", "\t.\n.\t.", "  -   ".
        r"(?P<spaced_ellipsis>\s*\.\s+\.\s+\.\s*)"  # ". . ." with any
        # whitespace between
        r"|(?P<dot_run>\.{2,})"  # "..", "...", "....", etc.
        r"|(?P<fullwidth_dot_run>．{2,})"  # "．．．" (and longer)
        r"|(?P<middle_dot_run>・{3,})"  # "・・・" (and longer)
        # Hyphen-as-dash only when surrounded by whitespace,
        # but allow variable whitespace.
        r"|(?P<spaced_double_hyphen>\s+--\s+)"  # " -- " (or tabs/newlines)
        r"|(?P<double_hyphen>--)"  # "--"
        r"|(?P<spaced_hyphen>\s+-\s+)"  # " - " (or tabs/newlines)
    )

    # Build once (important: normalization wins over
    # removal, matching your if/elif order)
    _CHAR_MAP: ClassVar[dict[str, str | None]] = {
        k: v for k, v in PUNCTUATION_NORMALIZATION.items() if len(k) == 1
    }
    for _ch in REMOVE_PUNCTUATION:
        # Replacing with space is safer than deletion: it avoids merging words
        # like "hello/world" -> "helloworld".
        _CHAR_MAP.setdefault(_ch, " ")
    _TRANSLATE_TABLE: ClassVar[dict[int, str | None]] = str.maketrans(_CHAR_MAP)

    @classmethod
    def _replace_seq(cls, m: re.Match[str]) -> str:
        g = m.lastgroup
        if g in ("spaced_ellipsis", "dot_run", "fullwidth_dot_run", "middle_dot_run"):
            return "…"
        if g in ("spaced_double_hyphen", "spaced_hyphen"):
            return " — "
        if g == "double_hyphen":
            return "—"
        return m.group(0)

    def normalize(self, text: str) -> str:
        """Normalize Unicode punctuation to Kokoro-compatible equivalents.

        Args:
            text: Input text with various Unicode punctuation.

        Returns:
            Text with normalized punctuation.

        Examples:
            >>> punct = Punctuation()
            >>> punct.normalize("Hello… world！")
            'Hello… world!'
            >>> punct.normalize('"Hello," she said.')
            '"Hello," she said.'
            >>> punct.normalize("Wait...what?!")
            'Wait…what?!'
            >>> punct.normalize("don't worry")
            "don't worry"
            >>> punct.normalize("Wait - now")
            'Wait — now'
        """
        text = self._SEQ_RE.sub(self._replace_seq, text)
        return text.translate(self._TRANSLATE_TABLE)

    def remove(self, text: str | list[str]) -> str | list[str]:
        """Remove all punctuation marks, replacing with spaces.

        Args:
            text: Input text or list of texts.

        Returns:
            Text(s) with punctuation replaced by spaces.

        Examples:
            >>> punct = Punctuation()
            >>> punct.remove("Hello, world!")
            'Hello world'
            >>> punct.remove(["Hello!", "How are you?"])
            ['Hello', 'How are you']
        """

        def _remove_single(t: str) -> str:
            t = self.normalize(t)
            return self._marks_re.sub(" ", t).strip() if self._marks_re else t

        if isinstance(text, str):
            return _remove_single(text)
        return [_remove_single(t) for t in text]

    def preserve(self, text: str | list[str]) -> tuple[list[str], list[MarkIndex]]:
        """Extract punctuation from text, preserving positions for restoration.

        This splits the text into chunks without punctuation, while recording
        where each punctuation mark was located.

        Args:
            text: Input text or list of texts.

        Returns:
            Tuple of (text_chunks, mark_indices) where:
            - text_chunks: List of text segments without punctuation
            - mark_indices: List of MarkIndex objects for restoration

        Examples:
            >>> punct = Punctuation()
            >>> text, marks = punct.preserve('Hello, world!')
            >>> text
            ['Hello', 'world']
            >>> [(m.mark, m.position.value) for m in marks]
            [(', ', 'I'), ('!', 'E')]
        """
        if isinstance(text, str):
            text = [text]

        preserved_text: list[str] = []
        preserved_marks: list[MarkIndex] = []

        for num, line in enumerate(text):
            line_text, line_marks = self._preserve_line(line, num)
            preserved_text.extend(line_text)
            preserved_marks.extend(line_marks)

        return [t for t in preserved_text if t], preserved_marks

    def _preserve_line(self, line: str, num: int) -> tuple[list[str], list[MarkIndex]]:
        """Preserve punctuation for a single line."""
        if self._marks_re is None:
            return [line], []

        matches = list(re.finditer(self._marks_re, line))
        if not matches:
            return [line], []

        # Line is only punctuation
        if len(matches) == 1 and matches[0].group() == line:
            return [], [MarkIndex(num, line, Position.ALONE)]

        # Build list of mark indices
        marks: list[MarkIndex] = []
        for match in matches:
            # Determine position: Begin, End, Middle, or Alone
            position = Position.MIDDLE
            if match == matches[0] and line.startswith(match.group()):
                position = Position.BEGIN
            elif match == matches[-1] and line.endswith(match.group()):
                position = Position.END
            marks.append(MarkIndex(num, match.group(), position))

        # Split line into segments
        preserved_line: list[str] = []
        remaining = line
        for mark in marks:
            parts = remaining.split(mark.mark, 1)
            preserved_line.append(parts[0])
            remaining = parts[1] if len(parts) > 1 else ""

        return preserved_line + [remaining], marks

    @classmethod
    def restore(
        cls,
        text: str | list[str],
        marks: list[MarkIndex],
        word_sep: str = " ",
        strip: bool = True,
    ) -> list[str]:
        """Restore punctuation to phonemized text.

        This is the reverse of preserve(). It takes phonemized text chunks
        and reinserts the punctuation marks at their original positions.

        Args:
            text: Phonemized text chunks.
            marks: Mark indices from preserve().
            word_sep: Word separator used in phonemized output.
            strip: Whether to strip trailing separators.

        Returns:
            List of phonemized text with punctuation restored.

        Examples:
            >>> punct = Punctuation()
            >>> text, marks = punct.preserve('Hello, world!')
            >>> punct.restore(['həˈloʊ', 'wˈɜːld'], marks)
            ['həˈloʊ, wˈɜːld!']
        """
        if isinstance(text, str):
            text = [text]
        text = list(text)  # Make a copy
        marks = list(marks)  # Do not mutate caller's list (we pop in some branches)
        punctuated: list[str] = []
        pos = 0
        while text or marks:
            if not marks:
                # No more marks, append remaining text
                for line in text:
                    if not strip and word_sep and not line.endswith(word_sep):
                        line = line + word_sep
                    punctuated.append(line)
                text = []

            elif not text:
                # No more text chunks, but still marks left.
                # Emit punctuation-only lines grouped by their original index,
                # preserving line boundaries (and filling gaps if needed).
                while marks:
                    next_idx = marks[0].index

                    # If there are missing lines between current
                    # pos and next mark index,
                    # preserve the line count by emitting empty lines.
                    while pos < next_idx:
                        punctuated.append("" if strip else (word_sep or ""))
                        pos += 1

                    # Collect all marks for this line index
                    same_line: list[MarkIndex] = []
                    while marks and marks[0].index == next_idx:
                        same_line.append(marks.pop(0))

                    mark_str = "".join(m.mark for m in same_line)
                    mark_str = re.sub(r" ", word_sep, mark_str)

                    suffix = "" if strip or mark_str.endswith(word_sep) else word_sep
                    punctuated.append(mark_str + suffix)
                    pos += 1

            else:
                current_mark = marks[0]
                if current_mark.index == pos:
                    # Place the current mark
                    mark = marks[0]
                    marks = marks[1:]
                    mark_str = re.sub(r" ", word_sep, mark.mark)

                    # Remove trailing word separator from current text
                    if word_sep and text[0].endswith(word_sep):
                        text[0] = text[0][: -len(word_sep)]

                    if current_mark.position == Position.BEGIN:
                        text[0] = mark_str + text[0]
                    elif current_mark.position == Position.END:
                        suffix = (
                            "" if strip or mark_str.endswith(word_sep) else word_sep
                        )
                        punctuated.append(text[0] + mark_str + suffix)
                        text = text[1:]
                        pos += 1
                    elif current_mark.position == Position.ALONE:
                        suffix = (
                            "" if strip or mark_str.endswith(word_sep) else word_sep
                        )
                        punctuated.append(mark_str + suffix)
                        pos += 1
                    else:
                        # Position.MIDDLE
                        if len(text) == 1:
                            text[0] = text[0] + mark_str
                        else:
                            first = text[0]
                            text = text[1:]
                            text[0] = first + mark_str + text[0]
                else:
                    punctuated.append(text[0])
                    text = text[1:]
                    pos += 1

        return punctuated


# =============================================================================
# Utility functions
# =============================================================================


def normalize_punctuation(text: str) -> str:
    """Normalize Unicode punctuation to Kokoro-compatible equivalents.

    This is a convenience function that creates a Punctuation instance
    and calls normalize().

    Args:
        text: Input text with various Unicode punctuation.

    Returns:
        Text with normalized punctuation.

    Examples:
        >>> normalize_punctuation("Hello… world！")
        'Hello… world!'
    """
    return Punctuation().normalize(text)


def filter_punctuation(text: str) -> str:
    """Keep only Kokoro-supported punctuation, remove everything else.

    Args:
        text: Input text.

    Returns:
        Text with only Kokoro-supported punctuation.

    Examples:
        >>> filter_punctuation("Hello~world!")
        'Hello world!'
    """
    punct = Punctuation()
    normalized = punct.normalize(text)
    # Remove any remaining unsupported punctuation.
    # Special-case: keep ASCII hyphen '-' when it is *word-internal*
    # (e.g. mother-in-law),
    # because some lexica contain hyphenated entries and
    # we want the token to remain intact.
    result: list[str] = []
    for i, char in enumerate(normalized):
        keep_inword_hyphen = (
            char == "-"
            and 0 < i < len(normalized) - 1
            and normalized[i - 1].isalnum()
            and normalized[i + 1].isalnum()
        )
        if (
            char.isalnum()
            or char.isspace()
            or char in KOKORO_PUNCTUATION
            # Keep ASCII apostrophe for contractions after
            # normalization (don’t -> don't)
            or char == "'"
            or keep_inword_hyphen
        ):
            result.append(char)
        # Skip unsupported punctuation
    return "".join(result)


def is_kokoro_punctuation(char: str) -> bool:
    """Check if a character is a Kokoro-supported punctuation mark.

    Args:
        char: Single character to check.

    Returns:
        True if the character is in Kokoro's punctuation vocabulary.
    """
    return char in KOKORO_PUNCTUATION
