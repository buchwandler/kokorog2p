"""Espeak-only G2P for languages without dedicated dictionaries.

This module provides a simple G2P implementation that uses espeak-ng
directly for phonemization. It's used as a fallback for languages
that don't have dedicated dictionary-based G2P implementations.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import re

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken


class EspeakOnlyG2P(G2PBase):
    """G2P implementation using only espeak-ng.

    This is used for languages that don't have dedicated dictionaries
    or custom G2P logic. It provides basic phonemization via espeak.

    Example:
        >>> g2p = EspeakOnlyG2P("fr-fr")
        >>> tokens = g2p("Bonjour le monde")
    """

    # Mapping from language codes to espeak voice names
    VOICE_MAP = {
        # European languages
        "fr": "fr-fr",
        "fr-fr": "fr-fr",
        "de": "de",
        "de-de": "de",
        "es": "es",
        "es-es": "es",
        "it": "it",
        "it-it": "it",
        "pt": "pt",
        "pt-pt": "pt",
        "pt-br": "pt-br",
        "nl": "nl",
        "nl-nl": "nl",
        "pl": "pl",
        "pl-pl": "pl",
        "ru": "ru",
        "ru-ru": "ru",
        "cs": "cs",
        "cs-cz": "cs",
        "sv": "sv",
        "sv-se": "sv",
        "da": "da",
        "da-dk": "da",
        "fi": "fi",
        "fi-fi": "fi",
        "no": "nb",
        "nb": "nb",
        "nb-no": "nb",
        "el": "el",
        "el-gr": "el",
        "tr": "tr",
        "tr-tr": "tr",
        "hu": "hu",
        "hu-hu": "hu",
        "ro": "ro",
        "ro-ro": "ro",
        "uk": "uk",
        "uk-ua": "uk",
        # Asian languages
        "vi": "vi",
        "vi-vn": "vi",
        "th": "th",
        "th-th": "th",
        "id": "id",
        "id-id": "id",
        "ms": "ms",
        "ms-my": "ms",
        # Other
        "ar": "ar",
        "ar-sa": "ar",
        "he": "he",
        "he-il": "he",
        "hi": "hi",
        "hi-in": "hi",
        "bn": "bn",
        "bn-in": "bn",
        "ta": "ta",
        "ta-in": "ta",
        "fa": "fa",
        "fa-ir": "fa",
    }

    def __init__(
        self,
        language: str = "en-us",
        use_espeak_fallback: bool = True,  # Always True for this class
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the espeak-only G2P.

        Args:
            language: Language code (e.g., 'fr-fr', 'de-de').
            use_espeak_fallback: Ignored (always uses espeak).
            version: Model version (default: "1.0").
            **kwargs: Additional arguments (ignored).
        """
        super().__init__(language=language, use_espeak_fallback=True)
        self.version = version
        self._espeak_backend = None
        self._espeak_voice = self._get_espeak_voice(language)

    def _get_espeak_voice(self, language: str) -> str:
        """Get espeak voice name for language code."""
        lang = language.lower().replace("_", "-")
        if lang in self.VOICE_MAP:
            return self.VOICE_MAP[lang]
        # Try base language (e.g., 'fr' from 'fr-ca')
        base_lang = lang.split("-")[0]
        if base_lang in self.VOICE_MAP:
            return self.VOICE_MAP[base_lang]
        # Default to the language code itself
        return lang

    @property
    def espeak_backend(self):
        """Lazy initialization of espeak backend."""
        if self._espeak_backend is None:
            from kokorog2p.backends.espeak import EspeakBackend

            self._espeak_backend = EspeakBackend(
                language=self._espeak_voice,
                with_stress=True,
            )
        return self._espeak_backend

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

            # Phonemize using espeak
            try:
                phonemes = self.espeak_backend.word_phonemes(part)
            except Exception:
                phonemes = None

            token = GToken(
                text=part,
                tag="X",  # Unknown tag
                whitespace="",
                phonemes=phonemes if phonemes else None,
            )
            token.rating = "espeak" if phonemes else None
            tokens.append(token)

        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word using espeak.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for espeak).

        Returns:
            Phoneme string from espeak.
        """
        try:
            return self.espeak_backend.word_phonemes(word)
        except Exception:
            return None

    def phonemize(self, text: str) -> str:
        """Convert text to phonemes using espeak.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string.
        """
        try:
            return self.espeak_backend.phonemize(text)
        except Exception:
            return ""

    def __repr__(self) -> str:
        return (
            f"EspeakOnlyG2P(language={self.language!r}, voice={self._espeak_voice!r})"
        )
