"""Goruut-only G2P for languages supported by pygoruut.

This module provides a simple G2P implementation that uses pygoruut
directly for phonemization. It's an alternative to espeak-based G2P
for languages supported by goruut.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import re

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken


class GoruutOnlyG2P(G2PBase):
    """G2P implementation using only pygoruut/goruut.

    This is used as an alternative to espeak for languages that
    pygoruut supports well. It provides phonemization via the
    goruut engine.

    Example:
        >>> g2p = GoruutOnlyG2P("fr")
        >>> tokens = g2p("Bonjour le monde")
    """

    def __init__(
        self,
        language: str = "en-us",
        use_espeak_fallback: bool = False,  # Not used for this class
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the goruut-only G2P.

        Args:
            language: Language code (e.g., 'fr', 'de', 'en-us').
            use_espeak_fallback: Ignored (always uses goruut).
            version: Model version (default: "1.0").
            **kwargs: Additional arguments (ignored).
        """
        super().__init__(language=language, use_espeak_fallback=False)
        self.version = version
        self._goruut_backend = None

    @property
    def goruut_backend(self):
        """Lazy initialization of goruut backend."""
        if self._goruut_backend is None:
            from kokorog2p.backends.goruut import GoruutBackend

            self._goruut_backend = GoruutBackend(
                language=self.language,
                with_stress=True,
            )
        return self._goruut_backend

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes.
        """
        if not text or not text.strip():
            return []

        tokens = []

        # Simple tokenization by whitespace and punctuation
        # Split keeping punctuation as separate tokens
        pattern = r"(\s+|[,.!?;:\"'()\[\]{}—–\-])"
        parts = re.split(pattern, text)

        for part in parts:
            if not part:
                continue

            if part.isspace():
                # Add whitespace to previous token
                if tokens:
                    tokens[-1].whitespace = part
                continue

            # Check if punctuation
            if len(part) == 1 and part in ",.!?;:\"'()[]{}—–-":
                token = GToken(
                    text=part,
                    tag="PUNCT",
                    whitespace="",
                    phonemes=part,  # Keep punctuation as-is
                )
                tokens.append(token)
                continue

            # Phonemize using goruut
            try:
                phonemes = self.goruut_backend.word_phonemes(part)
            except Exception:
                phonemes = None

            token = GToken(
                text=part,
                tag="X",  # Unknown tag
                whitespace="",
                phonemes=phonemes if phonemes else None,
            )
            token.rating = "goruut" if phonemes else None
            tokens.append(token)

        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word using goruut.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for goruut).

        Returns:
            Phoneme string from goruut.
        """
        try:
            return self.goruut_backend.word_phonemes(word)
        except Exception:
            return None

    def phonemize(self, text: str) -> str:
        """Convert text to phonemes using goruut.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string.
        """
        try:
            return self.goruut_backend.phonemize(text)
        except Exception:
            return ""

    @staticmethod
    def is_available() -> bool:
        """Check if pygoruut is available.

        Returns:
            True if pygoruut can be imported.
        """
        try:
            from kokorog2p.backends.goruut import GoruutBackend

            return GoruutBackend.is_available()
        except ImportError:
            return False

    def __repr__(self) -> str:
        return f"GoruutOnlyG2P(language={self.language!r})"
