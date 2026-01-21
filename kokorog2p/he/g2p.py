"""Hebrew G2P (Grapheme-to-Phoneme) converter.

This module provides Hebrew text to phoneme conversion using the phonikud package.
The phonikud package handles Hebrew text with diacritics (nikud) and converts it to IPA.

Based on phonikud package: https://github.com/thewh1teagle/phonikud

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import warnings
from typing import Any

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions


class HebrewG2P(G2PBase):
    """Hebrew G2P using phonikud for phonemization.

    This class converts Hebrew text to phonemes using the phonikud package.
    Hebrew text is expected to be with enhanced diacritics (nikud) for accurate
    phonemization.

    Example:
        >>> g2p = HebrewG2P()
        >>> tokens = g2p("שָׁלוֹם")  # "shalom" with nikud
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    def __init__(
        self,
        language: str = "he",
        use_espeak_fallback: bool = False,
        use_goruut_fallback: bool = False,
        load_silver: bool = True,
        load_gold: bool = True,
        preserve_punctuation: bool = True,
        preserve_stress: bool = True,
        version: str = "1.0",
        **kwargs: Any,
    ) -> None:
        """Initialize the Hebrew G2P.

        Args:
            language: Language code (e.g., 'he', 'he-il', 'heb', 'hebrew').
            use_espeak_fallback: Whether to use espeak for unknown words.
                Not typically used for Hebrew. Defaults to False.
            use_goruut_fallback: Whether to use goruut for unknown words.
                Not typically used for Hebrew. Defaults to False.
            load_silver: Reserved for API consistency. Hebrew doesn't use
                dictionary tiers. Defaults to True.
            load_gold: Reserved for API consistency. Hebrew doesn't use
                dictionary tiers. Defaults to True.
            preserve_punctuation: Whether to preserve punctuation in output.
                Defaults to True.
            preserve_stress: Whether to preserve stress markers in output.
                Defaults to True.
            **kwargs: Additional arguments passed to phonikud.phonemize().
        """
        super().__init__(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
        )
        self.version = version
        self.load_silver = load_silver
        self.load_gold = load_gold
        self.preserve_punctuation = preserve_punctuation
        self.preserve_stress = preserve_stress
        self.phonikud_kwargs = kwargs
        self._phonikud = None

    @property
    def phonikud(self):
        """Lazy initialization of phonikud backend."""
        if self._phonikud is None:
            try:
                import phonikud

                self._phonikud = phonikud
            except ImportError as e:
                warnings.warn(
                    f"phonikud not available: {e}. "
                    "Hebrew G2P requires phonikud package. "
                    "Install it with: pip install phonikud",
                    stacklevel=2,
                )
                self._phonikud = None
        return self._phonikud

    def __call__(self, text: str) -> list[GToken]:
        """Convert Hebrew text to tokens with phonemes.

        Args:
            text: Input Hebrew text to convert (preferably with nikud).

        Returns:
            List of GToken objects with phonemes.
        """
        if not text or not text.strip():
            return []

        if self.phonikud is None:
            # Return tokens without phonemes if phonikud is not available
            tokens = [GToken(text=text, tag="HE", whitespace="", phonemes=None)]
            ensure_gtoken_positions(tokens, text)
            return tokens

        # Convert to phonemes using phonikud
        try:
            phonemes = self.phonikud.phonemize(
                text,
                preserve_punctuation=self.preserve_punctuation,
                preserve_stress=self.preserve_stress,
                **self.phonikud_kwargs,
            )
        except Exception as e:
            warnings.warn(
                f"phonikud phonemization failed: {e}. Returning original text.",
                stacklevel=2,
            )
            phonemes = None

        # Create a single token with the phoneme string
        token = GToken(
            text=text,
            tag="HE",
            whitespace="",
            phonemes=phonemes if phonemes else None,
        )
        token.rating = "he" if phonemes else None
        tokens = [token]
        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a Hebrew word and return its phonetic representation.

        Args:
            word: The word to look up (preferably with nikud).
            tag: Optional POS tag (not used in Hebrew G2P).

        Returns:
            Phoneme string or None if phonikud is not available.
        """
        if not word or not word.strip():
            return None

        if self.phonikud is None:
            return None

        try:
            phonemes = self.phonikud.phonemize(
                word,
                preserve_punctuation=self.preserve_punctuation,
                preserve_stress=self.preserve_stress,
                **self.phonikud_kwargs,
            )
            return phonemes if phonemes else None
        except Exception:
            return None

    def _phonemize_internal(self, text: str) -> tuple[str, list[GToken] | None]:
        """Internal phonemization logic.

        Args:
            text: Input text.

        Returns:
            Tuple of (phoneme_string, token_list).
        """
        if self.phonikud is None:
            return "", None

        try:
            phonemes = self.phonikud.phonemize(
                text,
                preserve_punctuation=self.preserve_punctuation,
                preserve_stress=self.preserve_stress,
                **self.phonikud_kwargs,
            )
        except Exception:
            return "", None

        # Create a token
        token = GToken(
            text=text,
            tag="HE",
            whitespace="",
            phonemes=phonemes if phonemes else None,
        )
        token.rating = "he" if phonemes else None

        return phonemes or "", [token] if phonemes else None

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
