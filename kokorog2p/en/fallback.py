"""Fallback options for OOV words with IPA to Kokoro conversion."""

import logging
from typing import TYPE_CHECKING

from kokorog2p.fallback_base import FallbackBase
from kokorog2p.phonemes import from_espeak, from_goruut

if TYPE_CHECKING:
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.backends.goruut import GoruutBackend

logger = logging.getLogger(__name__)


class EspeakFallback(FallbackBase["EspeakBackend"]):
    """Fallback G2P using espeak-ng with Kokoro phoneme conversion."""

    install_hint = "Check that espeak-ng is properly installed."
    backend_word_kokoro = False
    backend_text_kokoro = True

    def __init__(self, british: bool = False, use_cli: bool = False) -> None:
        """Initialize the espeak fallback.

        Args:
            british: Whether to use British English.
        """
        super().__init__(use_cli=use_cli)
        self.british = british

    def _create_backend(self) -> "EspeakBackend":
        from kokorog2p.backends.espeak import EspeakBackend

        language = "en-gb" if self.british else "en-us"
        return EspeakBackend(language=language, use_cli=self.use_cli)

    def _postprocess_word(self, phonemes: str) -> str:
        return from_espeak(phonemes, british=self.british)

    def _postprocess_text(self, phonemes: str) -> str:
        # backend already returns Kokoro format when backend_text_kokoro=True
        return phonemes


class GoruutFallback(FallbackBase["GoruutBackend"]):
    """Fallback G2P using goruut with Kokoro phoneme conversion."""

    install_hint = "Check that pygoruut is properly installed."
    backend_word_kokoro = False
    backend_text_kokoro = True

    def __init__(self, british: bool = False) -> None:
        """Initialize the goruut fallback.

        Args:
            british: Whether to use British English.
        """
        super().__init__()
        self.british = british

    def _create_backend(self) -> "GoruutBackend":
        from kokorog2p.backends.goruut import GoruutBackend

        language = "en-gb" if self.british else "en-us"
        return GoruutBackend(language=language)

    def _postprocess_word(self, phonemes: str) -> str:
        return from_goruut(phonemes, british=self.british)

    def _postprocess_text(self, phonemes: str) -> str:
        # backend already returns Kokoro format when backend_text_kokoro=True
        return phonemes
