"""High-level espeak backend for Kokoro TTS phonemization.

This module provides a convenient interface for converting text to phonemes
using espeak-ng, with automatic conversion to Kokoro's phoneme format.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import re
from typing import cast

from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer
from kokorog2p.backends.espeak.phonemizer_base import EspeakPhonemizerBase
from kokorog2p.backends.espeak.wrapper import Phonemizer
from kokorog2p.phonemes import from_espeak


class EspeakBackend:
    """High-level espeak backend for Kokoro TTS phonemization.

    This class provides a simple interface for converting text to phonemes
    using espeak-ng. It automatically converts espeak's IPA output to
    Kokoro's phoneme format.

    Example:
        >>> backend = EspeakBackend("en-us")
        >>> backend.phonemize("hello world")
        'hˈɛlO wˈɜɹld'
    """

    def __init__(
        self,
        language: str = "en-us",
        with_stress: bool = True,
        tie: str = "^",
        use_cli: bool = False,
    ) -> None:
        """Initialize the espeak backend.

        Args:
            language: Language code (e.g., "en-us", "en-gb", "fr-fr").
            with_stress: Whether to include stress markers in output.
            tie: Tie character mode. "^" uses tie character for affricates.
            use_cli: If True, force use of CLI phonemizer instead of library.
        """
        self.language = language
        self.with_stress = with_stress
        self.tie = tie
        self.use_cli = use_cli
        self._phonemizer: EspeakPhonemizerBase | None = None

    @property
    def wrapper(self) -> EspeakPhonemizerBase:
        """Get the underlying Phonemizer instance (lazy initialization)."""
        if self._phonemizer is None and not self.use_cli:
            try:
                self._phonemizer = Phonemizer()
                self._phonemizer.set_voice(self.language)
            except Exception:
                self._phonemizer = CliPhonemizer(
                    language=self.language, tie_char=self.tie
                )
        elif self._phonemizer is None and self.use_cli:
            self._phonemizer = CliPhonemizer(language=self.language, tie_char=self.tie)
        if self._phonemizer is not None and self._phonemizer.voice is None:
            try:
                self._phonemizer.set_voice(self.language)
            except Exception:
                if not isinstance(self._phonemizer, CliPhonemizer):
                    self._phonemizer = CliPhonemizer(
                        language=self.language, tie_char=self.tie
                    )
        return cast(EspeakPhonemizerBase, self._phonemizer)

    @property
    def is_british(self) -> bool:
        """Check if using British English variant."""
        return self.language.lower() in ("en-gb", "en_gb")

    def remove_punctuation(self, text: str) -> str:
        """Remove punctuation from text before phonemization.

        Preserves:
        - Hyphens between letters: "my-world" → "my-world"
        - Apostrophes between letters: "don't" → "don't"
        - Single periods between letters: "Dr. Smith" → "Dr. Smith"

        Removes:
        - Quote marks around words: "'Hello'" → "Hello"
        - Repeated punctuation: "Hello??" → "Hello?"
        - Standalone punctuation: "!" → "", "?" → ""
        - Standalone dots: ".." → ""
        - Ellipsis sequences: "I like this ... . Hello." → "I like this. Hello."
        - Special sequences: "I dont't like you.!" → "I dont't like you."

        Enforces:
        - Single punctuation between words
        - Space after punctuation: "Hello,world" → "Hello, world"

        Preserves special symbols: @, #, etc.

        Args:
            text: Input text.

        Returns:
            Text with punctuation cleaned.
        """
        # Placeholders for protected characters
        APOS_PROTECT = "__APOS__"
        HYPHEN_PROTECT = "__HYPHEN__"

        # Step 1: Protect apostrophes between letters (contractions)
        text = re.sub(r"(?<=\w)'(?=\w)", APOS_PROTECT, text)

        # Step 2: Protect hyphens between letters (compound words)
        text = re.sub(r"(?<=\w)-(?=\w)", HYPHEN_PROTECT, text)

        # Step 3: Remove quote marks (single and double)
        text = re.sub(r"[\"']", "", text)

        # Step 4: Remove spaces before punctuation
        text = re.sub(r"\s+([.,;:!?])", r"\1", text)

        # Step 5: Collapse repeated punctuation (?!;: to single)
        text = re.sub(r"([?!;:,])\1+", r"\1", text)

        # Step 6: Collapse dot sequences
        # First, handle ellipsis-like patterns: "..." becomes "."
        # But keep single period between letters (abbreviations)
        text = re.sub(r"\.{2,}", ".", text)

        # Step 7: Remove standalone punctuation (not attached to words)
        # Remove standalone !, ?, ;, : not between letters
        text = re.sub(r"(?<!\w)[?!;:,](?!\w)", "", text)

        # Step 8: Remove standalone dots
        text = re.sub(r"(?<!\w)\.(?!\w)", "", text)

        # Step 9: Clean up multiple spaces
        text = re.sub(r" +", " ", text)

        # Step 10: Enforce space after punctuation when followed by letter
        text = re.sub(r"([.,;:!?])(?=\w)", r"\1 ", text)

        # Step 11: Restore protected characters
        text = text.replace(APOS_PROTECT, "'")
        text = text.replace(HYPHEN_PROTECT, "-")

        # Step 12: Strip leading/trailing whitespace
        text = text.strip()

        return text

    def phonemize(
        self,
        text: str,
        convert_to_kokoro: bool = True,
        remove_punctuation: bool = True,
    ) -> str:
        """Convert text to phonemes.

        Args:
            text: Text to convert to phonemes.
            convert_to_kokoro: If True, convert espeak IPA to Kokoro format.
                              If False, return raw espeak IPA output.
            remove_punctuation: If True, remove punctuation before phonemization.
        Returns:
            Phoneme string.
        """
        # Use tie character for better handling of affricates (dʒ, tʃ)
        use_tie = self.tie == "^"
        if remove_punctuation:
            text = self.remove_punctuation(text)
        raw_phonemes = self.wrapper.phonemize(text, use_tie=use_tie)

        if convert_to_kokoro:
            return from_espeak(raw_phonemes, british=self.is_british)
        return raw_phonemes

    def phonemize_list(
        self,
        texts: list[str],
        convert_to_kokoro: bool = True,
    ) -> list[str]:
        """Convert multiple texts to phonemes.

        Args:
            texts: List of texts to convert.
            convert_to_kokoro: If True, convert to Kokoro format.

        Returns:
            List of phoneme strings.
        """
        return [self.phonemize(text, convert_to_kokoro) for text in texts]

    def word_phonemes(
        self,
        word: str,
        convert_to_kokoro: bool = True,
    ) -> str:
        """Convert a single word to phonemes.

        Args:
            word: Word to convert.
            convert_to_kokoro: If True, convert to Kokoro format.

        Returns:
            Phoneme string for the word (without separators).
        """
        result = self.phonemize(word, convert_to_kokoro)
        # Clean up: remove separators and trailing whitespace
        return result.strip().replace("_", "")

    @property
    def version(self) -> str:
        """Get espeak version as string (e.g., "1.51.1")."""
        return ".".join(str(v) for v in self.wrapper.version)

    def __repr__(self) -> str:
        return f"EspeakBackend(language={self.language!r})"
