"""Fallback options for French OOV words."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kokorog2p.fallback_base import FallbackBase

if TYPE_CHECKING:
    from kokorog2p.backends.espeak import EspeakBackend
    from kokorog2p.backends.goruut import GoruutBackend


class _FrenchNormalizeMixin:
    def _normalize_french_phonemes(self, phonemes: str) -> str:
        """Normalize French phonemes from backends."""
        mappings: dict[str, str] = {
            # R variants -> uvular R
            "ʀ": "ʁ",
            "r": "ʁ",
            "ɹ": "ʁ",
            # G variants
            "g": "ɡ",
        }

        result = phonemes
        for old, new in mappings.items():
            result = result.replace(old, new)

        # Remove stress marks (French doesn't have lexical stress)
        return result.replace("ˈ", "").replace("ˌ", "")


class FrenchFallback(_FrenchNormalizeMixin, FallbackBase["EspeakBackend"]):
    """Fallback G2P using espeak-ng for French."""

    backend_word_kokoro = False
    backend_text_kokoro = False

    def _create_backend(self) -> EspeakBackend:
        from kokorog2p.backends.espeak import EspeakBackend

        return EspeakBackend(language="fr", use_cli=self.use_cli)

    def _postprocess_word(self, phonemes: str) -> str:
        return self._normalize_french_phonemes(phonemes)


class FrenchGoruutFallback(_FrenchNormalizeMixin, FallbackBase["GoruutBackend"]):
    """Fallback G2P using goruut for French."""

    backend_word_kokoro = False
    backend_text_kokoro = False

    def _create_backend(self) -> GoruutBackend:
        from kokorog2p.backends.goruut import GoruutBackend

        return GoruutBackend(language="fr-fr")

    def _postprocess_word(self, phonemes: str) -> str:
        return self._normalize_french_phonemes(phonemes)
