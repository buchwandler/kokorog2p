# kokorog2p/fallback_base.py
"""Base classes for OOV fallback phonemizers.

Design goals:
- Lazy backend initialization (import-heavy backends)
- Uniform call contract: (phonemes|None, rating)
- Centralized error handling/logging
- Simple hooks for conversion/normalization
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

logger = logging.getLogger(__name__)

B = TypeVar("B")


class FallbackBase(ABC, Generic[B]):
    """Base class for fallback G2P implementations.

    Subclasses must implement:
      - _create_backend()
      - _postprocess_word()

    Optionally override:
      - _postprocess_text() (default: uses _postprocess_word)
      - _backend_word_phonemes() / _backend_phonemize() if backend API differs
      - _log_backend_error() / _log_word_error() to customize logging
    """

    #: Rating returned on success (commonly 1). On failure returns 0.
    success_rating: int = 1

    #: If True, pass convert_to_kokoro=True into backend.word_phonemes().
    backend_word_kokoro: bool = False

    #: If True, pass convert_to_kokoro=True into backend.phonemize().
    backend_text_kokoro: bool = False

    #: Extra hint appended to backend-init error logs (RuntimeError).
    install_hint: str = ""

    def __init__(self, use_cli: bool = False) -> None:
        self.use_cli = use_cli
        self._backend: B | None = None

    @property
    def backend(self) -> B:
        """Lazily initialize the backend."""
        if self._backend is None:
            self._backend = self._create_backend()
        return self._backend

    @abstractmethod
    def _create_backend(self) -> B:
        """Create and return the backend instance (called once lazily)."""

    # ---- backend interaction (override if your backend differs) ----

    def _backend_word_phonemes(self, word: str) -> str:
        """Get raw phonemes for a single word from the backend."""
        return self.backend.word_phonemes(  # type: ignore[attr-defined]
            word,
            convert_to_kokoro=self.backend_word_kokoro,
        )

    def _backend_phonemize(self, text: str) -> str:
        """Get raw phonemes for text from the backend."""
        return self.backend.phonemize(  # type: ignore[attr-defined]
            text,
            convert_to_kokoro=self.backend_text_kokoro,
        )

    # ---- postprocessing hooks ----

    @abstractmethod
    def _postprocess_word(self, phonemes: str) -> str:
        """Convert/normalize backend output for a single word."""

    def _postprocess_text(self, phonemes: str) -> str:
        """Convert/normalize backend output for a text string."""
        return self._postprocess_word(phonemes)

    # ---- logging hooks ----

    def _log_backend_error(self, word: str, err: Exception) -> None:
        hint = f" {self.install_hint}" if self.install_hint else ""
        logger.error(
            "%s failed for word %r: %s.%s",
            self.__class__.__name__,
            word,
            err,
            hint,
        )

    def _log_word_error(self, word: str, err: Exception) -> None:
        logger.warning(
            "%s could not process word %r: %s",
            self.__class__.__name__,
            word,
            err,
        )

    # ---- public API ----

    def __call__(self, word: str) -> tuple[str | None, int]:
        """Return (phonemes|None, rating). Rating is 0 on failure."""
        try:
            raw = self._backend_word_phonemes(word)
            if not raw:
                return (None, 0)
            return (self._postprocess_word(raw), self.success_rating)
        except RuntimeError as e:
            self._log_backend_error(word, e)
            return (None, 0)
        except Exception as e:
            self._log_word_error(word, e)
            return (None, 0)

    def phonemize(self, text: str) -> str:
        """Phonemize text using backend + postprocessing."""
        raw = self._backend_phonemize(text)
        if not raw:
            return ""
        return self._postprocess_text(raw)
