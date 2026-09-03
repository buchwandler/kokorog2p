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
from collections import OrderedDict
from collections.abc import Sequence
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

        self._word_cache: OrderedDict[tuple[object, ...], tuple[str | None, int]] = (
            OrderedDict()
        )
        self._word_cache_maxsize = 1024

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

    def _postprocess_batch_raw(self, phonemes: str) -> str:
        """Normalize one raw result returned by a batch backend."""
        return phonemes

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

    def _word_cache_key(self, word: str) -> tuple[object, ...]:
        backend = self.backend
        info = getattr(backend, "info", None)
        implementation = getattr(info, "implementation", type(backend).__name__)
        data_path = getattr(backend, "data_path", None)
        voice = getattr(backend, "language", None)
        voice_language = getattr(backend, "voice_language", None)
        return (
            self.__class__.__qualname__,
            voice,
            voice_language,
            implementation,
            str(data_path) if data_path is not None else None,
            word,
            getattr(backend, "tie", None),
            getattr(backend, "sep", None),
            self.backend_word_kokoro,
            self.backend_text_kokoro,
        )

    def _cache_get(self, key: tuple[object, ...]) -> tuple[str | None, int] | None:
        result = self._word_cache.get(key)
        if result is not None:
            self._word_cache.move_to_end(key)
        return result

    def _cache_put(
        self, key: tuple[object, ...], result: tuple[str | None, int]
    ) -> None:
        self._word_cache[key] = result
        self._word_cache.move_to_end(key)
        while len(self._word_cache) > self._word_cache_maxsize:
            self._word_cache.popitem(last=False)

    # ---- public API ----

    def __call__(self, word: str) -> tuple[str | None, int]:
        """Return (phonemes|None, rating). Rating is 0 on failure."""
        try:
            key = self._word_cache_key(word)
            cached = self._cache_get(key)
            if cached is not None:
                return cached
            raw = self._backend_word_phonemes(word)
            result = (
                (None, 0)
                if not raw
                else (self._postprocess_word(raw), self.success_rating)
            )
            self._cache_put(key, result)
            return result
        except RuntimeError as e:
            self._log_backend_error(word, e)
            return (None, 0)
        except Exception as e:
            self._log_word_error(word, e)
            return (None, 0)

    def phonemize_many(self, words: Sequence[str]) -> list[tuple[str | None, int]]:
        """Phonemize independently framed words through one backend instance."""
        values = list(words)
        backend_many = getattr(self.backend, "phonemize_many", None)
        if not callable(backend_many):
            return [self(word) for word in values]

        keys: list[tuple[object, ...]] = []
        results: list[tuple[str | None, int] | None] = [None] * len(values)
        pending: list[tuple[int, str]] = []
        for index, word in enumerate(values):
            key = self._word_cache_key(word)
            keys.append(key)
            cached = self._cache_get(key)
            if cached is None:
                pending.append((index, word))
            else:
                results[index] = cached
        if pending:
            try:
                raw_results = backend_many(
                    [word for _, word in pending],
                    convert_to_kokoro=self.backend_text_kokoro,
                )
            except Exception as exc:
                self._log_backend_error("<batch>", exc)
                for index, word in pending:
                    results[index] = self(word)
            else:
                if len(raw_results) != len(pending):
                    raise RuntimeError("Backend returned an invalid batch length")
                for (index, _), raw in zip(pending, raw_results, strict=True):
                    result = (
                        (None, 0)
                        if not raw
                        else (
                            self._postprocess_word(self._postprocess_batch_raw(raw)),
                            self.success_rating,
                        )
                    )
                    self._cache_put(keys[index], result)
                    results[index] = result
        return [result for result in results if result is not None]

    def phonemize(self, text: str) -> str:
        """Phonemize text using backend + postprocessing."""
        raw = self._backend_phonemize(text)
        if not raw:
            return ""
        return self._postprocess_text(raw)
