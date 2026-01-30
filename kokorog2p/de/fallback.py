"""Fallback options for German OOV words."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kokorog2p.fallback_base import FallbackBase

if TYPE_CHECKING:
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.backends.goruut import GoruutBackend


class _GermanNormalizeMixin:
    def _normalize_german_phonemes(self, phonemes: str) -> str:
        """Normalize German phonemes from backends."""
        from kokorog2p.de.g2p import normalize_to_kokoro

        result = normalize_to_kokoro(phonemes)

        # Additional backend-agnostic normalizations
        mappings: dict[str, str] = {
            # Remove tie characters (seen in espeak output sometimes)
            "͡": "",
            "^": "",
        }
        for old, new in mappings.items():
            result = result.replace(old, new)
        return result


class GermanEspeakFallback(_GermanNormalizeMixin, FallbackBase["EspeakBackend"]):
    """Fallback G2P using espeak-ng for German."""

    backend_word_kokoro = False
    backend_text_kokoro = False

    def _create_backend(self) -> EspeakBackend:
        from kokorog2p.backends.espeak import EspeakBackend

        return EspeakBackend(language="de", use_cli=self.use_cli)

    def _postprocess_word(self, phonemes: str) -> str:
        return self._normalize_german_phonemes(phonemes)


class GermanGoruutFallback(_GermanNormalizeMixin, FallbackBase["GoruutBackend"]):
    """Fallback G2P using goruut for German."""

    backend_word_kokoro = False
    backend_text_kokoro = False

    def _create_backend(self) -> GoruutBackend:
        from kokorog2p.backends.goruut import GoruutBackend

        return GoruutBackend(language="de-de")

    def _postprocess_word(self, phonemes: str) -> str:
        return self._normalize_german_phonemes(phonemes)
