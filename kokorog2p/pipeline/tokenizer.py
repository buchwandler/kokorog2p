"""Tokenization framework for the G2P pipeline.

Provides abstract base classes and implementations for tokenizing text
into ProcessingToken objects with position tracking and metadata.
"""

import re
from abc import ABC, abstractmethod
from typing import Any

from kokorog2p.abbreviation_utils import merge_abbreviation_tokens
from kokorog2p.pipeline.models import ProcessingToken


def _merge_abbreviation_tokens(
    tokens: list[ProcessingToken],
    lang: str | None,
) -> list[ProcessingToken]:
    def is_break(
        prev: ProcessingToken, current: ProcessingToken, last_end: int
    ) -> bool:
        if prev.whitespace:
            return True
        if current.char_start != last_end and current.char_start != 0:
            return True
        return False

    def build_token(
        start: ProcessingToken,
        end: ProcessingToken,
        text: str,
    ) -> ProcessingToken:
        return ProcessingToken(
            text=text,
            char_start=start.char_start,
            char_end=end.char_end,
            whitespace=end.whitespace,
        )

    return merge_abbreviation_tokens(
        tokens,
        lang,
        is_break=is_break,
        build_token=build_token,
    )


class BaseTokenizer(ABC):
    """Abstract base class for tokenization.

    Tokenizers convert normalized text into a list of ProcessingToken objects,
    tracking positions, quotes, and other metadata.
    """

    def __init__(
        self,
        track_positions: bool = True,
        phoneme_quotes: str = "curly",
        lang: str | None = None,
    ):
        """Initialize the tokenizer.

        Args:
            track_positions: Whether to track character positions in text
            phoneme_quotes: Quote style for phoneme output:
                - "curly": Use directional quotes " and " (default)
                - "ascii": Use ASCII double quote "
                - "none": Strip quotes from phoneme output
            lang: Optional language code for abbreviation merging.
        """
        self.track_positions = track_positions
        self.phoneme_quotes = phoneme_quotes
        self.lang = lang

        # Validate phoneme_quotes parameter
        if phoneme_quotes not in ("curly", "ascii", "none"):
            raise ValueError(
                f"phoneme_quotes must be 'curly', 'ascii', or 'none', "
                f"got {phoneme_quotes!r}"
            )

    @abstractmethod
    def tokenize(
        self, text: str, normalized_text: str | None = None
    ) -> list[ProcessingToken]:
        """Tokenize text into ProcessingToken objects.

        Args:
            text: Original text to tokenize
            normalized_text: Normalized version of text (if different from text)

        Returns:
            List of ProcessingToken objects
        """
        pass

    def _detect_quote_depth(
        self, tokens: list[ProcessingToken], use_bracket_matching: bool = True
    ) -> None:
        """Detect and assign quote nesting depth to tokens.

        Modifies tokens in-place, setting the quote_depth attribute.

        Args:
            tokens: List of tokens to process
            use_bracket_matching: If True, use bracket-matching for nesting.
                                 If False, use simple alternation.
        """
        if use_bracket_matching:
            self._bracket_matching_quotes(tokens)
        else:
            self._simple_alternating_quotes(tokens)

    def _bracket_matching_quotes(self, tokens: list[ProcessingToken]) -> None:
        """Use stack-based nesting for quote directionality.

        Implements true nesting support when using different quote characters.
        Each quote type can nest within another, and depth increases with nesting level.

        Nested quotes are ONLY supported when using different quote chars:
        - ✅ Supported: "outer `inner` text" (different) → [1, 2, 2, 1]
        - ❌ NOT supported: "level1 "level2"" (same) → [1, 1, 1, 1]

        Algorithm:
        - Maintains a stack of open quote characters
        - When encountering a quote:
          * If no matching quote type in stack → OPEN (push, depth=size)
          * If matching quote found → CLOSE (pop, depth=current size)
        - Depth represents nesting level (1 = outermost, 2 = nested once, etc.)
        - Different quote types (", `, ') can nest within each other
        - Same quote type alternates (open/close pairs, no nesting)

        Examples:
        - "hello" → depths [1, 1] (simple pair)
        - "outer `inner` text" → depths [1, 2, 2, 1] (nested)
        - "first" and "second" → depths [1, 1, 1, 1] (two separate pairs)
        - "a `b 'c' d` e" → depths [1, 2, 3, 3, 2, 1] (triple nesting)

        Args:
            tokens: List of tokens to process (modified in-place)
        """
        # Stack to track open quotes - stores the quote character (", `, ')
        stack: list[str] = []

        # Quote characters we recognize
        quote_chars = frozenset(('"', "`", "'"))

        for token in tokens:
            # Check if this token is a quote character
            if token.text in quote_chars:
                quote_char = token.text

                # Search for matching opening quote of the same type in the stack
                matching_open_index = None
                for i in range(len(stack) - 1, -1, -1):
                    if stack[i] == quote_char:
                        matching_open_index = i
                        break

                if matching_open_index is None:
                    # Opening quote - no matching quote type in stack
                    stack.append(quote_char)
                    token.quote_depth = len(stack)
                else:
                    # Closing quote - found matching opening quote
                    # Pop the mathcing quote first
                    stack.pop(matching_open_index)
                    # The nassign depth AFTER popping (depth = stack size after
                    # close)
                    token.quote_depth = len(stack)
            else:
                # Non-quote token - inherit depth from current nesting level
                # Depth = number of quotes currently open
                token.quote_depth = len(stack)

    def _simple_alternating_quotes(self, tokens: list[ProcessingToken]) -> None:
        """Use simple alternation for quote directionality.

        Does NOT handle nested quotes properly.
        Pattern: 1st quote opens (depth 1), 2nd quote closes (depth 0), etc.

        Args:
            tokens: List of tokens to process (modified in-place)
        """
        quote_count = 0
        current_depth = 0

        for token in tokens:
            if token.text in ('"', "`", "'"):
                quote_count += 1
                if quote_count % 2 == 1:
                    # Opening quote
                    current_depth = 1
                    token.quote_depth = 1
                else:
                    # Closing quote
                    token.quote_depth = 0
                    current_depth = 0
            else:
                # Non-quote token
                token.quote_depth = current_depth

    def _convert_quote_direction(self, tokens: list[ProcessingToken]) -> None:
        """Convert straight quotes to curly quotes based on quote_depth.

        Even depth (0, 2, 4...) or depth transitions use left curly quote (")
        Odd depth (1, 3, 5...) or closing use right curly quote (")

        Modifies token.text in-place.

        Args:
            tokens: List of tokens to process (modified in-place)
        """
        prev_depth = 0

        for token in tokens:
            if token.text == '"':
                # Opening quote (depth increases) → left curly
                # Closing quote (depth decreases) → right curly
                if token.quote_depth > prev_depth:
                    token.text = "\u201c"  # "
                else:
                    token.text = "\u201d"  # "
                prev_depth = token.quote_depth
            elif token.text == "`":
                # Backticks follow same pattern as double quotes
                if token.quote_depth > prev_depth:
                    token.text = "\u201c"  # "
                else:
                    token.text = "\u201d"  # "
                prev_depth = token.quote_depth
            elif token.text == "'":
                # Single quotes follow same pattern as double quotes
                if token.quote_depth > prev_depth:
                    token.text = "\u201c"  # "
                else:
                    token.text = "\u201d"  # "
                prev_depth = token.quote_depth
            else:
                prev_depth = token.quote_depth

    def normalize_phoneme_quotes(self, text: str) -> str:
        """Normalize quote characters for phoneme output based on setting.

        Args:
            text: Text potentially containing quote characters

        Returns:
            Text with quotes normalized according to phoneme_quotes setting
        """
        if self.phoneme_quotes == "ascii":
            # Convert all quote variants to ASCII
            text = text.replace("\u201c", '"').replace("\u201d", '"').replace("`", '"')
        elif self.phoneme_quotes == "none":
            # Strip all quotes
            text = (
                text.replace('"', "")
                .replace("\u201c", "")
                .replace("\u201d", "")
                .replace("`", "")
            )
        # else: "curly" - keep as-is

        return text


class RegexTokenizer(BaseTokenizer):
    """Simple regex-based tokenizer.

    Uses regex patterns to split text into words, contractions, punctuation,
    and whitespace. Does not perform POS tagging.
    """

    def __init__(
        self,
        track_positions: bool = True,
        use_bracket_matching: bool = True,
        phoneme_quotes: str = "curly",
        contraction_pattern: str | None = None,
        lang: str | None = None,
    ):
        """Initialize the regex tokenizer.

        Args:
            track_positions: Whether to track character positions
            use_bracket_matching: Whether to use bracket-matching for quotes
            phoneme_quotes: Quote style for phoneme output
            contraction_pattern: Custom regex pattern for contractions
                                (default: handles standard English contractions)
            lang: Optional language code for abbreviation merging.
        """
        super().__init__(track_positions, phoneme_quotes, lang)
        self.use_bracket_matching = use_bracket_matching

        # Default pattern for English contractions
        if contraction_pattern is None:
            # Matches:
            # 1. Words with apostrophes (contractions): \w+'\w+
            # 2. Regular words: \w+
            # 3. Single punctuation: [^\w\s]
            # 4. Whitespace: \s+
            self.pattern = re.compile(r"(\w+'\w+|\w+|[^\w\s]|\s+)")
        else:
            self.pattern = re.compile(contraction_pattern)

    def tokenize(
        self, text: str, normalized_text: str | None = None
    ) -> list[ProcessingToken]:
        """Tokenize text using regex patterns.

        Args:
            text: Text to tokenize (already normalized)
            normalized_text: Not used (same as text for regex tokenizer)

        Returns:
            List of ProcessingToken objects
        """
        tokens: list[ProcessingToken] = []

        for match in self.pattern.finditer(text):
            word = match.group()

            # Skip whitespace - attach to previous token instead
            if word.isspace():
                if tokens:
                    tokens[-1].whitespace = word
                continue

            # Create token with position tracking
            token = ProcessingToken(
                text=word,
                char_start=match.start() if self.track_positions else 0,
                char_end=match.end() if self.track_positions else 0,
                whitespace="",
            )

            tokens.append(token)

        tokens = _merge_abbreviation_tokens(tokens, self.lang)

        # Detect quote nesting
        self._detect_quote_depth(tokens, use_bracket_matching=self.use_bracket_matching)

        # Convert straight quotes to curly based on nesting
        self._convert_quote_direction(tokens)

        return tokens


class SpacyTokenizer(BaseTokenizer):
    """SpaCy-based tokenizer with POS tagging.

    Uses spaCy's NLP pipeline for tokenization and part-of-speech tagging.
    Provides more accurate tokenization and grammatical information.
    """

    def __init__(
        self,
        nlp: Any,  # spacy.Language object
        track_positions: bool = True,
        use_bracket_matching: bool = True,
        phoneme_quotes: str = "curly",
        lang: str | None = None,
    ):
        """Initialize the spaCy tokenizer.

        Args:
            nlp: spaCy Language object (e.g., spacy.load("en_core_web_sm"))
            track_positions: Whether to track character positions
            use_bracket_matching: Whether to use bracket-matching for quotes
            phoneme_quotes: Quote style for phoneme output
            lang: Optional language code for abbreviation merging.
        """
        super().__init__(track_positions, phoneme_quotes, lang)
        self.nlp = nlp
        self.use_bracket_matching = use_bracket_matching

    def tokenize(
        self, text: str, normalized_text: str | None = None
    ) -> list[ProcessingToken]:
        """Tokenize text using spaCy.

        Args:
            text: Text to tokenize (already normalized)
            normalized_text: Not used (same as text for spaCy tokenizer)

        Returns:
            List of ProcessingToken objects with POS tags
        """
        doc = self.nlp(text)
        tokens: list[ProcessingToken] = []

        for tk in doc:
            token = ProcessingToken(
                text=tk.text,
                pos_tag=tk.tag_,
                char_start=tk.idx if self.track_positions else 0,
                char_end=tk.idx + len(tk.text) if self.track_positions else 0,
                whitespace=tk.whitespace_,
            )
            tokens.append(token)

        # Detect quote nesting
        self._detect_quote_depth(tokens, use_bracket_matching=self.use_bracket_matching)

        # Convert spaCy quote tags to curly quotes
        self._convert_spacy_quotes(tokens)

        # Convert straight quotes to curly based on nesting depth
        self._convert_quote_direction(tokens)

        return tokens

    def _convert_spacy_quotes(self, tokens: list[ProcessingToken]) -> None:
        """Convert spaCy's quote tags (`` and '') to curly quotes.

        For quotes that are already curly (from normalization), we preserve
        their directionality. For straight quotes, we ignore spaCy's tags
        and use quote_depth from alternation instead.

        Args:
            tokens: List of tokens to process (modified in-place)
        """
        for token in tokens:
            # If already curly, preserve as-is (normalization has set directionality)
            if token.text in "\u201c\u201d":
                # Already curly - directionality is correct from normalization
                continue

            # For straight quotes, we rely on quote_depth from alternation
            # (not spaCy's tags which can be unreliable for simple alternating quotes)
            # The _convert_quote_direction method will handle conversion
