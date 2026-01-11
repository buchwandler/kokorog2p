"""Fallback options for OOV words with IPA to Kokoro conversion."""

import logging
from typing import TYPE_CHECKING

from kokorog2p.phonemes import from_espeak, from_goruut

if TYPE_CHECKING:
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.backends.goruut import GoruutBackend

logger = logging.getLogger(__name__)


class EspeakFallback:
    """Fallback G2P using espeak-ng with Kokoro phoneme conversion."""

    def __init__(self, british: bool = False) -> None:
        """Initialize the espeak fallback.

        Args:
            british: Whether to use British English.
        """
        self.british = british
        self._backend: EspeakBackend | None = None  # Lazy init  # noqa: F821

    @property
    def backend(self) -> "EspeakBackend":  # noqa: F821
        """Lazily initialize the espeak backend."""
        if self._backend is None:
            from kokorog2p.backends.espeak import EspeakBackend

            language = "en-gb" if self.british else "en-us"
            self._backend = EspeakBackend(language=language)
        return self._backend

    def __call__(self, word: str) -> tuple[str | None, int]:
        """Get phonemes for a word using espeak.

        Args:
            word: Word to phonemize.

        Returns:
            Tuple of (phonemes, rating). Rating is 1 for espeak fallback.
        """
        try:
            # Get phonemes from espeak
            raw_phonemes = self.backend.word_phonemes(word, convert_to_kokoro=False)
            if not raw_phonemes:
                return (None, 0)

            # Convert to Kokoro format
            phonemes = from_espeak(raw_phonemes, british=self.british)
            return (phonemes, 1)
        except RuntimeError as e:
            # espeak backend initialization or critical failure
            logger.error(
                f"EspeakFallback failed for word '{word}': {e}. "
                f"Check that espeak-ng is properly installed."
            )
            return (None, 0)
        except Exception as e:
            # Per-word processing errors can be graceful
            logger.warning(f"EspeakFallback could not process word '{word}': {e}")
            return (None, 0)

    def phonemize(self, text: str) -> str:
        """Phonemize text using espeak.

        Args:
            text: Text to phonemize.

        Returns:
            Phoneme string in Kokoro format.
        """
        return self.backend.phonemize(text, convert_to_kokoro=True)


class GoruutFallback:
    """Fallback G2P using goruut with Kokoro phoneme conversion."""

    def __init__(self, british: bool = False) -> None:
        """Initialize the goruut fallback.

        Args:
            british: Whether to use British English.
        """
        self.british = british
        self._backend: GoruutBackend | None = None  # Lazy init  # noqa: F821

    @property
    def backend(self) -> "GoruutBackend":  # noqa: F821
        """Lazily initialize the goruut backend."""
        if self._backend is None:
            from kokorog2p.backends.goruut import GoruutBackend

            language = "en-gb" if self.british else "en-us"
            self._backend = GoruutBackend(language=language)
        return self._backend

    def __call__(self, word: str) -> tuple[str | None, int]:
        """Get phonemes for a word using goruut.

        Args:
            word: Word to phonemize.

        Returns:
            Tuple of (phonemes, rating). Rating is 1 for goruut fallback.
        """
        try:
            # Get phonemes from goruut
            raw_phonemes = self.backend.word_phonemes(word, convert_to_kokoro=False)
            if not raw_phonemes:
                return (None, 0)

            # Convert to Kokoro format
            phonemes = from_goruut(raw_phonemes, british=self.british)
            return (phonemes, 1)
        except RuntimeError as e:
            # goruut backend initialization or critical failure
            logger.error(
                f"GoruutFallback failed for word '{word}': {e}. "
                f"Check that pygoruut is properly installed."
            )
            return (None, 0)
        except Exception as e:
            # Per-word processing errors can be graceful
            logger.warning(f"GoruutFallback could not process word '{word}': {e}")
            return (None, 0)

    def phonemize(self, text: str) -> str:
        """Phonemize text using goruut.

        Args:
            text: Text to phonemize.

        Returns:
            Phoneme string in Kokoro format.
        """
        return self.backend.phonemize(text, convert_to_kokoro=True)
