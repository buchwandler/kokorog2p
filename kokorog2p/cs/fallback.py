"""Fallback options for Czech OOV words."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kokorog2p.fallback_base import FallbackBase

if TYPE_CHECKING:
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.backends.goruut import GoruutBackend


class _CzechNormalizeMixin:
    def _normalize_czech_phonemes(self, phonemes: str) -> str:
        """Normalize Czech phonemes from backends."""
        mappings: dict[str, str] = {
            # G variants
            "g": "ɡ",
            # Remove tie characters (may appear in espeak output)
            "͡": "",
            "^": "",
            # Remove stress marks (Czech has fixed stress on first syllable)
            "ˈ": "",
            "ˌ": "",
        }

        result = phonemes
        for old, new in mappings.items():
            result = result.replace(old, new)
        return result


class CzechEspeakFallback(_CzechNormalizeMixin, FallbackBase["EspeakBackend"]):
    """Fallback G2P using espeak-ng for Czech."""

    backend_word_kokoro = False
    backend_text_kokoro = False

    def _create_backend(self) -> EspeakBackend:
        from kokorog2p.backends.espeak import EspeakBackend

        return EspeakBackend(language="cs", use_cli=self.use_cli)

    def _postprocess_word(self, phonemes: str) -> str:
        return self._normalize_czech_phonemes(phonemes)


class CzechGoruutFallback(_CzechNormalizeMixin, FallbackBase["GoruutBackend"]):
    """Fallback G2P using goruut for Czech."""

    backend_word_kokoro = False
    backend_text_kokoro = False

    def _create_backend(self) -> GoruutBackend:
        from kokorog2p.backends.goruut import GoruutBackend

        return GoruutBackend(language="cs")

    def _postprocess_word(self, phonemes: str) -> str:
        return self._normalize_czech_phonemes(phonemes)
