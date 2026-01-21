"""Goruut-only G2P for languages supported by pygoruut.

This module provides a simple G2P implementation that uses pygoruut
directly for phonemization. It's an alternative to espeak-based G2P
for languages supported by goruut.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import logging
import re

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

logger = logging.getLogger(__name__)


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
        use_goruut_fallback: bool = True,  # Not used for this class
        strict: bool = True,
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the goruut-only G2P.

        Args:
            language: Language code (e.g., 'fr', 'de', 'en-us').
            use_espeak_fallback: Ignored (always uses goruut).
            use_goruut_fallback: Ignored (always uses goruut).
            strict: If True (default), raise exceptions on errors. If False,
                log warnings and return empty results for backward compatibility.
            version: Model version (default: "1.0").
            **kwargs: Additional arguments (ignored).
        """
        super().__init__(
            language=language,
            use_espeak_fallback=False,
            use_goruut_fallback=True,
            strict=strict,
        )
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
            except Exception as e:
                if self.strict:
                    if isinstance(e, RuntimeError):
                        raise RuntimeError(
                            f"GoruutOnlyG2P failed to process word '{part}' "
                            f"with goruut. This usually means pygoruut is not "
                            f"properly installed or initialized. "
                            f"Original error: {e}"
                        ) from e
                    else:
                        raise RuntimeError(
                            f"Unexpected error processing word '{part}': {e}"
                        ) from e
                else:
                    logger.error(
                        f"GoruutOnlyG2P failed to process word '{part}': {e}. "
                        f"Returning None (strict=False mode)."
                    )
                    phonemes = None

            token = GToken(
                text=part,
                tag="X",  # Unknown tag
                whitespace="",
                phonemes=phonemes if phonemes else None,
            )
            token.rating = "goruut" if phonemes else None
            tokens.append(token)

        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word using goruut.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for goruut).

        Returns:
            Phoneme string from goruut, or None if strict=False and error occurs.

        Raises:
            RuntimeError: If goruut backend fails and strict=True.
        """
        try:
            return self.goruut_backend.word_phonemes(word)
        except Exception as e:
            if self.strict:
                if isinstance(e, RuntimeError):
                    raise RuntimeError(
                        f"GoruutOnlyG2P.lookup() failed for word '{word}' with goruut. "
                        f"Original error: {e}"
                    ) from e
                else:
                    raise RuntimeError(
                        f"Unexpected error in lookup for '{word}': {e}"
                    ) from e
            else:
                logger.error(
                    f"GoruutOnlyG2P.lookup() failed for word '{word}': {e}. "
                    f"Returning None (strict=False mode)."
                )
                return None

    def phonemize(self, text: str) -> str:
        """Convert text to phonemes using goruut.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string, or empty string if strict=False and error occurs.

        Raises:
            RuntimeError: If goruut backend fails and strict=True.
        """
        try:
            return self.goruut_backend.phonemize(text)
        except Exception as e:
            if self.strict:
                if isinstance(e, RuntimeError):
                    # goruut initialization or configuration errors
                    raise RuntimeError(
                        f"GoruutOnlyG2P failed to phonemize text with goruut. "
                        f"This usually means pygoruut is not properly "
                        f"installed or initialized. Original error: {e}"
                    ) from e
                else:
                    # Unexpected errors - don't hide them!
                    raise RuntimeError(
                        f"Unexpected error in GoruutOnlyG2P.phonemize(): {e}"
                    ) from e
            else:
                logger.error(
                    f"GoruutOnlyG2P.phonemize() failed: {e}. "
                    f"Returning empty string (strict=False mode)."
                )
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
