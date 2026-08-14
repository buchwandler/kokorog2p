"""High-level goruut backend for Kokoro TTS phonemization.

This module provides a convenient interface for converting text to phonemes
using pygoruut (goruut), with automatic conversion to Kokoro's phoneme format.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

from typing import Optional

from kokorog2p.phonemes import from_goruut

# Language mapping from standard codes to pygoruut language names
LANGUAGE_MAP: dict[str, str] = {
    # English variants
    "en": "EnglishAmerican",
    "en-us": "EnglishAmerican",
    "en_us": "EnglishAmerican",
    "en-gb": "EnglishBritish",
    "en_gb": "EnglishBritish",
    "english": "EnglishAmerican",
    # Major languages
    "fr": "French",
    "fr-fr": "French",
    "de": "German",
    "de-de": "German",
    "es": "Spanish",
    "es-es": "Spanish",
    "it": "Italian",
    "it-it": "Italian",
    "pt": "Portuguese",
    "pt-pt": "Portuguese",
    "pt-br": "Portuguese",
    "nl": "Dutch",
    "nl-nl": "Dutch",
    "pl": "Polish",
    "pl-pl": "Polish",
    "ru": "Russian",
    "ru-ru": "Russian",
    "ja": "Japanese",
    "ja-jp": "Japanese",
    "ko": "Korean",
    "ko-kr": "Korean",
    "zh": "ChineseMandarin",
    "zh-cn": "ChineseMandarin",
    "cmn": "ChineseMandarin",
    "yue": "Cantonese",
    "zh-hk": "Cantonese",
    # Nordic languages
    "sv": "Swedish",
    "sv-se": "Swedish",
    "da": "Danish",
    "da-dk": "Danish",
    "no": "Norwegian",
    "no-no": "Norwegian",
    "fi": "Finnish",
    "fi-fi": "Finnish",
    "is": "Icelandic",
    "is-is": "Icelandic",
    # Other European languages
    "cs": "Czech",
    "cs-cz": "Czech",
    "sk": "Slovak",
    "sk-sk": "Slovak",
    "hu": "Hungarian",
    "hu-hu": "Hungarian",
    "ro": "Romanian",
    "ro-ro": "Romanian",
    "bg": "Bulgarian",
    "bg-bg": "Bulgarian",
    "uk": "Ukrainian",
    "uk-ua": "Ukrainian",
    "el": "Greek",
    "el-gr": "Greek",
    "tr": "Turkish",
    "tr-tr": "Turkish",
    "hr": "Croatian",
    "hr-hr": "Croatian",
    "sr": "Serbian",
    "sr-rs": "Serbian",
    "sl": "Slovenian",
    "sl-si": "Slovenian",
    "et": "Estonian",
    "et-ee": "Estonian",
    "lv": "Latvian",
    "lv-lv": "Latvian",
    "lt": "Lithuanian",
    "lt-lt": "Lithuanian",
    "ca": "Catalan",
    "ca-es": "Catalan",
    "eu": "Basque",
    "eu-es": "Basque",
    "gl": "Galician",
    "gl-es": "Galician",
    # Asian languages
    "hi": "Hindi",
    "hi-in": "Hindi",
    "bn": "Bengali",
    "bn-in": "Bengali",
    "ta": "Tamil",
    "ta-in": "Tamil",
    "te": "Telugu",
    "te-in": "Telugu",
    "th": "Thai",
    "th-th": "Thai",
    "vi": "VietnameseNorthern",
    "vi-vn": "VietnameseNorthern",
    "id": "Indonesian",
    "id-id": "Indonesian",
    "ms": "MalayLatin",
    "ms-my": "MalayLatin",
    "tl": "Tagalog",
    "fil": "Tagalog",
    # Middle Eastern languages
    "ar": "Arabic",
    "ar-sa": "Arabic",
    "he": "Hebrew",
    "he-il": "Hebrew",
    "fa": "Farsi",
    "fa-ir": "Farsi",
    "ur": "Urdu",
    "ur-pk": "Urdu",
    # African languages
    "sw": "Swahili",
    "sw-ke": "Swahili",
    "af": "Afrikaans",
    "af-za": "Afrikaans",
    # Other languages
    "eo": "Esperanto",
}


# Singleton instance for the pygoruut process
_goruut_instance: Optional["Pygoruut"] = None  # noqa: F821
_GORUUT_STARTUP_RETRIES = 3


def _get_goruut() -> "Pygoruut":  # noqa: F821
    """Get or create the singleton pygoruut instance."""
    global _goruut_instance
    if _goruut_instance is None:
        from pygoruut.pygoruut import Pygoruut

        for attempt in range(_GORUUT_STARTUP_RETRIES):
            try:
                _goruut_instance = Pygoruut(writeable_bin_dir="")
                break
            except RuntimeError as exc:
                # pygoruut >= 0.8.1 reports a process that exits while its
                # HTTP server is coming up. Retrying gives its random port a
                # chance to avoid a transient Windows port collision.
                if (
                    "exited before becoming ready" not in str(exc)
                    or attempt == _GORUUT_STARTUP_RETRIES - 1
                ):
                    raise
    return _goruut_instance


class GoruutBackend:
    """High-level goruut backend for Kokoro TTS phonemization.

    This class provides a simple interface for converting text to phonemes
    using pygoruut. It automatically converts goruut's IPA output to
    Kokoro's phoneme format.

    Example:
        >>> backend = GoruutBackend("en-us")
        >>> backend.phonemize("hello world")
        'həlˈO wˈɜɹld'
    """

    def __init__(
        self,
        language: str = "en-us",
        with_stress: bool = True,
    ) -> None:
        """Initialize the goruut backend.

        Args:
            language: Language code (e.g., "en-us", "en-gb", "fr-fr").
            with_stress: Whether to include stress markers in output.
        """
        self.language = language.lower()
        self.with_stress = with_stress

        # Map to pygoruut language name
        self._goruut_language = LANGUAGE_MAP.get(self.language, self.language)

    @property
    def goruut(self) -> "Pygoruut":  # noqa: F821
        """Get the pygoruut instance (singleton, lazy initialization)."""
        return _get_goruut()

    @property
    def is_british(self) -> bool:
        """Check if using British English variant."""
        return self.language in ("en-gb", "en_gb")

    def phonemize(
        self,
        text: str,
        convert_to_kokoro: bool = True,
    ) -> str:
        """Convert text to phonemes.

        Args:
            text: Text to convert to phonemes.
            convert_to_kokoro: If True, convert goruut IPA to Kokoro format.
                              If False, return raw goruut IPA output.

        Returns:
            Phoneme string.
        """
        if not text.strip():
            return ""

        # Get phonemes from pygoruut
        result = self.goruut.phonemize(
            language=self._goruut_language,
            sentence=text,
            is_punct=True,
        )
        raw_phonemes = str(result)

        if convert_to_kokoro:
            return from_goruut(raw_phonemes, british=self.is_british)
        return raw_phonemes

    def phonemize_list(
        self,
        texts: list[str],
        convert_to_kokoro: bool = True,
    ) -> list[str]:
        """Convert multiple texts to phonemes.

        Args:
            texts: List of texts to convert.
            convert_to_kokoro: If True, convert to Kokoro format.

        Returns:
            List of phoneme strings.
        """
        return [self.phonemize(text, convert_to_kokoro) for text in texts]

    def word_phonemes(
        self,
        word: str,
        convert_to_kokoro: bool = True,
    ) -> str:
        """Convert a single word to phonemes.

        Args:
            word: Word to convert.
            convert_to_kokoro: If True, convert to Kokoro format.

        Returns:
            Phoneme string for the word (without separators).
        """
        result = self.phonemize(word, convert_to_kokoro)
        # Clean up: remove separators and trailing whitespace
        return result.strip().replace("_", "")

    @staticmethod
    def get_supported_languages() -> list[str]:
        """Get list of supported language codes.

        Returns:
            List of language codes that can be used with this backend.
        """
        return list(LANGUAGE_MAP.keys())

    @staticmethod
    def is_available() -> bool:
        """Check if pygoruut is available.

        Returns:
            True if pygoruut can be imported.
        """
        try:
            from pygoruut.pygoruut import Pygoruut  # noqa: F401

            return True
        except ImportError:
            return False

    def __repr__(self) -> str:
        return f"GoruutBackend(language={self.language!r})"
