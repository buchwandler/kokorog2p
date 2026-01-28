"""Espeak-only G2P for languages without dedicated dictionaries.

This module provides a simple G2P implementation that uses espeak-ng
directly for phonemization. It's used as a fallback for languages
that don't have dedicated dictionary-based G2P implementations.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import logging

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions, tokenize_with_offsets

logger = logging.getLogger(__name__)


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
        use_goruut_fallback: bool = False,  # Always False for this class
        strict: bool = True,
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the espeak-only G2P.

        Args:
            language: Language code (e.g., 'fr-fr', 'de-de').
            use_espeak_fallback: Ignored (always uses espeak).
            strict: If True (default), raise exceptions on errors. If False,
                log warnings and return empty results for backward compatibility.
            version: Model version (default: "1.0").
            **kwargs: Additional arguments (ignored).
        """
        super().__init__(
            language=language,
            use_espeak_fallback=True,
            use_goruut_fallback=False,
            strict=strict,
        )
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
        """Lazy initialization of espeak backend.

        Raises:
            RuntimeError: If espeak backend initialization or validation fails.
        """
        if self._espeak_backend is None:
            from kokorog2p.backends.espeak import EspeakBackend

            self._espeak_backend = EspeakBackend(
                language=self._espeak_voice,
                with_stress=True,
            )
            # Validate immediately after initialization
            self._validate_backend()
        return self._espeak_backend

    def _validate_backend(self) -> None:
        """Validate that espeak backend is working.

        This catches initialization failures early instead of
        during first phonemization attempt.

        Raises:
            RuntimeError: If espeak backend cannot phonemize test text.
        """
        if self._espeak_backend is None:
            raise RuntimeError("Backend not initialized")

        try:
            # Try a simple test
            test_result = self._espeak_backend.phonemize("test")
            if not test_result:
                raise RuntimeError(
                    f"Espeak backend returned empty result for test word. "
                    f"Voice '{self._espeak_voice}' may not be available."
                )
        except Exception as e:
            raise RuntimeError(
                f"Espeak backend validation failed. "
                f"Please ensure espeak-ng is properly installed and "
                f"voice '{self._espeak_voice}' is available. "
                f"Error: {e}"
            ) from e

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes.
        """
        if not text or not text.strip():
            return []

        tokens: list[GToken] = []
        token_spans = tokenize_with_offsets(text, keep_punct=True)
        for idx, span in enumerate(token_spans):
            next_start = (
                token_spans[idx + 1].char_start
                if idx + 1 < len(token_spans)
                else len(text)
            )
            whitespace = text[span.char_end : next_start]
            is_punct = not any(c.isalnum() for c in span.text)

            if is_punct:
                token = GToken(
                    text=span.text,
                    tag="PUNCT",
                    whitespace=whitespace,
                    phonemes=span.text,
                )
                token.set("char_start", span.char_start)
                token.set("char_end", span.char_end)
                tokens.append(token)
                continue

            try:
                phonemes = self.espeak_backend.word_phonemes(span.text)
            except Exception as e:
                if self.strict:
                    if isinstance(e, RuntimeError):
                        raise RuntimeError(
                            f"EspeakOnlyG2P failed to process word '{span.text}' "
                            f"with espeak-ng. This usually means espeak-ng is "
                            f"not properly installed or initialized. "
                            f"Original error: {e}"
                        ) from e
                    else:
                        raise RuntimeError(
                            f"Unexpected error processing word '{span.text}': {e}"
                        ) from e
                else:
                    logger.error(
                        f"EspeakOnlyG2P failed to process word '{span.text}': {e}. "
                        f"Returning None (strict=False mode)."
                    )
                    phonemes = None

            token = GToken(
                text=span.text,
                tag="X",
                whitespace=whitespace,
                phonemes=phonemes if phonemes else None,
            )
            token.rating = "espeak" if phonemes else None
            token.set("char_start", span.char_start)
            token.set("char_end", span.char_end)
            tokens.append(token)

        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word using espeak.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for espeak).

        Returns:
            Phoneme string from espeak, or None if strict=False and error occurs.

        Raises:
            RuntimeError: If espeak backend fails and strict=True.
        """
        try:
            return self.espeak_backend.word_phonemes(word)
        except Exception as e:
            if self.strict:
                if isinstance(e, RuntimeError):
                    raise RuntimeError(
                        f"EspeakOnlyG2P.lookup() failed for word '{word}' "
                        f"with espeak-ng. Original error: {e}"
                    ) from e
                else:
                    raise RuntimeError(
                        f"Unexpected error in lookup for '{word}': {e}"
                    ) from e
            else:
                logger.error(
                    f"EspeakOnlyG2P.lookup() failed for word '{word}': {e}. "
                    f"Returning None (strict=False mode)."
                )
                return None

    def phonemize(self, text: str) -> str:
        """Convert text to phonemes using espeak.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string, or empty string if strict=False and error occurs.

        Raises:
            RuntimeError: If espeak backend fails and strict=True.
        """
        try:
            return self.espeak_backend.phonemize(text)
        except Exception as e:
            if self.strict:
                if isinstance(e, RuntimeError):
                    # espeak initialization or configuration errors
                    raise RuntimeError(
                        f"EspeakOnlyG2P failed to phonemize text with "
                        f"espeak-ng. This usually means espeak-ng is not "
                        f"properly installed, the library cannot be found, "
                        f"or voice '{self._espeak_voice}' is unavailable. "
                        f"Original error: {e}"
                    ) from e
                else:
                    # Unexpected errors - don't hide them!
                    raise RuntimeError(
                        f"Unexpected error in EspeakOnlyG2P.phonemize(): {e}"
                    ) from e
            else:
                logger.error(
                    f"EspeakOnlyG2P.phonemize() failed: {e}. "
                    f"Returning empty string (strict=False mode)."
                )
                return ""

    def __repr__(self) -> str:
        return (
            f"EspeakOnlyG2P(language={self.language!r}, voice={self._espeak_voice!r})"
        )
