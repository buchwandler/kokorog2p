"""Mixed-language G2P with automatic language detection using lingua-py.

This module provides automatic language detection for mixed-language texts,
routing each word to the appropriate language-specific G2P engine.

Example:
    >>> from kokorog2p.mixed_language_g2p import MixedLanguageG2P
    >>> # German text with English words
    >>> g2p = MixedLanguageG2P(
    ...     primary_language="de",
    ...     allowed_languages=["de", "en-us"]
    ... )
    >>> result = g2p.phonemize("Ich gehe zum Meeting. Let's go!")
    >>> # Automatically detects and routes:
    >>> # - "Ich gehe zum" → German G2P
    >>> # - "Meeting Let's go" → English G2P
"""

import warnings
from typing import TYPE_CHECKING, Any, Final

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken

if TYPE_CHECKING:
    from lingua import Language, LanguageDetector

try:
    from lingua import Language, LanguageDetectorBuilder

    LINGUA_AVAILABLE = True
except ImportError:
    LINGUA_AVAILABLE = False
    Language = None  # type: ignore
    LanguageDetectorBuilder = None  # type: ignore

# =============================================================================
# Language Mapping Tables
# =============================================================================

# Map kokorog2p language codes to lingua Language enum
KOKOROG2P_TO_LINGUA: Final[dict[str, Any]] = {}
LINGUA_TO_KOKOROG2P: Final[dict[Any, str]] = {}

if LINGUA_AVAILABLE:
    # Populate mappings only if lingua is available
    KOKOROG2P_TO_LINGUA.update(
        {
            "en": Language.ENGLISH,  # type: ignore
            "en-us": Language.ENGLISH,  # type: ignore
            "en-gb": Language.ENGLISH,  # type: ignore
            "de": Language.GERMAN,  # type: ignore
            "de-de": Language.GERMAN,  # type: ignore
            "de-at": Language.GERMAN,  # type: ignore
            "de-ch": Language.GERMAN,  # type: ignore
            "fr": Language.FRENCH,  # type: ignore
            "fr-fr": Language.FRENCH,  # type: ignore
            "es": Language.SPANISH,  # type: ignore
            "es-es": Language.SPANISH,  # type: ignore
            "it": Language.ITALIAN,  # type: ignore
            "pt": Language.PORTUGUESE,  # type: ignore
            "pt-br": Language.PORTUGUESE,  # type: ignore
            "ja": Language.JAPANESE,  # type: ignore
            "ja-jp": Language.JAPANESE,  # type: ignore
            "zh": Language.CHINESE,  # type: ignore
            "zh-cn": Language.CHINESE,  # type: ignore
            "zh-tw": Language.CHINESE,  # type: ignore
            "ko": Language.KOREAN,  # type: ignore
            "ko-kr": Language.KOREAN,  # type: ignore
            "he": Language.HEBREW,  # type: ignore
            "he-il": Language.HEBREW,  # type: ignore
            "cs": Language.CZECH,  # type: ignore
            "cs-cz": Language.CZECH,  # type: ignore
            "nl": Language.DUTCH,  # type: ignore
            "pl": Language.POLISH,  # type: ignore
            "ru": Language.RUSSIAN,  # type: ignore
            "ar": Language.ARABIC,  # type: ignore
            "hi": Language.HINDI,  # type: ignore
            "tr": Language.TURKISH,  # type: ignore
        }
    )

    LINGUA_TO_KOKOROG2P.update(
        {
            Language.ENGLISH: "en-us",  # type: ignore  # Default to US English
            Language.GERMAN: "de",  # type: ignore
            Language.FRENCH: "fr",  # type: ignore
            Language.SPANISH: "es",  # type: ignore
            Language.ITALIAN: "it",  # type: ignore
            Language.PORTUGUESE: "pt",  # type: ignore
            Language.JAPANESE: "ja",  # type: ignore
            Language.CHINESE: "zh",  # type: ignore
            Language.KOREAN: "ko",  # type: ignore
            Language.HEBREW: "he",  # type: ignore
            Language.CZECH: "cs",  # type: ignore
            Language.DUTCH: "nl",  # type: ignore
            Language.POLISH: "pl",  # type: ignore
            Language.RUSSIAN: "ru",  # type: ignore
            Language.ARABIC: "ar",  # type: ignore
            Language.HINDI: "hi",  # type: ignore
            Language.TURKISH: "tr",  # type: ignore
        }
    )


class MixedLanguageG2P(G2PBase):
    """
    G2P converter with automatic word-level language detection.

    Uses lingua-py for high-accuracy language detection and routes each
    word to the appropriate language-specific G2P engine. Supports caching
    of detection results for improved performance.

    Attributes:
        primary_language: Main language of the text (fallback for ambiguous words)
        allowed_languages: List of languages that can be detected and processed
        confidence_threshold: Minimum confidence (0.0-1.0) to accept detection
        enable_detection: Whether language detection is active

    Example:
        >>> from kokorog2p import MixedLanguageG2P
        >>> # German text with English words
        >>> g2p = MixedLanguageG2P(
        ...     primary_language="de",
        ...     allowed_languages=["de", "en-us"]
        ... )
        >>> tokens = g2p("Das Meeting war great!")
        >>> for tok in tokens:
        ...     if tok.is_word:
        ...         print(f"{tok.text}: {tok.get('detected_language')}")
        Das: de
        Meeting: en-us
        war: de
        great: en-us
    """

    def __init__(
        self,
        primary_language: str = "en-us",
        allowed_languages: list[str] | None = None,
        confidence_threshold: float = 0.7,
        enable_detection: bool = True,
        version: str = "1.0",
        **kwargs: Any,
    ) -> None:
        """
        Initialize mixed-language G2P converter.

        Args:
            primary_language: Main language code (e.g., 'de', 'en-us').
                Used as fallback when detection fails or confidence is low.
            allowed_languages: List of language codes to detect and support.
                Must be explicitly specified by the user. Example: ["de", "en-us", "fr"]
            confidence_threshold: Minimum confidence (0.0-1.0) for accepting
                language detection. Words below this threshold fall back to
                primary_language. Default: 0.7 (recommended for balanced accuracy).
            enable_detection: If False, always uses primary_language (useful for
                debugging or when lingua-py is not available).
            version: Model version to pass to individual G2P instances (default: "1.0").
            **kwargs: Additional arguments passed to individual G2P instances
                (e.g., use_espeak_fallback, load_silver, load_gold).

        Raises:
            ValueError: If allowed_languages is None or empty.
            ImportError: If enable_detection=True but lingua-language-detector
                is not installed (will warn and disable detection instead).
        """
        super().__init__(language=primary_language)
        self.version = version

        if allowed_languages is None or len(allowed_languages) == 0:
            raise ValueError(
                "allowed_languages must be specified and non-empty. "
                "Example: allowed_languages=['de', 'en-us']"
            )

        # Check if lingua is available
        if not LINGUA_AVAILABLE:
            if enable_detection:
                warnings.warn(
                    "lingua-language-detector not available. "
                    "Mixed-language detection requires lingua-py.\n"
                    "Install it with: pip install kokorog2p[mixed]\n"
                    "or: pip install lingua-language-detector\n"
                    "Falling back to primary language only.",
                    UserWarning,
                    stacklevel=2,
                )
            enable_detection = False

        self.primary_language = primary_language
        self.allowed_languages = allowed_languages
        self.confidence_threshold = confidence_threshold
        self.enable_detection = enable_detection
        self.kwargs = kwargs

        # Initialize G2P instances for each language
        from kokorog2p import get_g2p

        self._g2p_instances: dict[str, G2PBase] = {}
        for lang in self.allowed_languages:
            # Avoid infinite recursion - don't pass multilingual_mode to sub-instances
            sub_kwargs = {k: v for k, v in kwargs.items() if k != "multilingual_mode"}
            self._g2p_instances[lang] = get_g2p(lang, **sub_kwargs)

        # Initialize lingua detector if available
        self._detector: LanguageDetector | None = None
        self._detection_cache: dict[str, str] = {}  # Cache: word -> language_code

        if LINGUA_AVAILABLE and enable_detection:
            lingua_languages = self._map_to_lingua_languages(self.allowed_languages)
            if lingua_languages:
                # Use preloaded models for better performance
                self._detector = (
                    LanguageDetectorBuilder.from_languages(*lingua_languages)  # type: ignore
                    .with_preloaded_language_models()
                    .build()
                )

    def _map_to_lingua_languages(self, lang_codes: list[str]) -> list[Any]:
        """
        Map kokorog2p language codes to lingua Language enum.

        Args:
            lang_codes: List of kokorog2p language codes (e.g., ["de", "en-us"]).

        Returns:
            List of lingua Language enum values (deduplicated).
        """
        if not LINGUA_AVAILABLE:
            return []

        result: list[Any] = []
        seen: set[Any] = set()

        for code in lang_codes:
            normalized = code.lower().replace("_", "-")
            if normalized in KOKOROG2P_TO_LINGUA:
                lingua_lang = KOKOROG2P_TO_LINGUA[normalized]
                if lingua_lang not in seen:
                    result.append(lingua_lang)
                    seen.add(lingua_lang)

        return result

    def _map_from_lingua_language(self, lingua_lang: Any) -> str:
        """
        Map lingua Language enum back to kokorog2p language code.

        Prefers exact match from allowed_languages if available.

        Args:
            lingua_lang: lingua Language enum value.

        Returns:
            kokorog2p language code (e.g., "de", "en-us").
        """
        if not LINGUA_AVAILABLE:
            return self.primary_language

        # Get base code from mapping
        base_code = LINGUA_TO_KOKOROG2P.get(lingua_lang, self.primary_language)

        # Prefer exact match if available in allowed_languages
        for allowed in self.allowed_languages:
            if allowed == base_code or allowed.startswith(base_code + "-"):
                return allowed

        return base_code

    def _detect_word_language(self, word: str) -> str:
        """
        Detect the language of a single word.

        Uses lingua-py for detection with caching. Falls back to primary
        language if detection is disabled, confidence is low, or word is
        too short/punctuation-heavy.

        Args:
            word: The word to detect language for.

        Returns:
            Language code (from allowed_languages or primary_language).
        """
        # Fast path: detection disabled
        if not self.enable_detection or self._detector is None:
            return self.primary_language

        # Fast path: check cache
        if word in self._detection_cache:
            return self._detection_cache[word]

        # Skip very short words and punctuation
        if len(word) < 3 or not any(c.isalnum() for c in word):
            return self.primary_language

        try:
            # Use lingua for detection with confidence values
            confidence_values = self._detector.compute_language_confidence_values(word)

            if not confidence_values:
                self._detection_cache[word] = self.primary_language
                return self.primary_language

            # Get highest confidence language
            best_match = confidence_values[0]

            # Check confidence threshold
            if best_match.value < self.confidence_threshold:
                self._detection_cache[word] = self.primary_language
                return self.primary_language

            # Map lingua Language back to kokorog2p code
            detected = self._map_from_lingua_language(best_match.language)

            # Ensure detected language is in allowed_languages
            if detected not in self._g2p_instances:
                self._detection_cache[word] = self.primary_language
                return self.primary_language

            # Cache and return
            self._detection_cache[word] = detected
            return detected

        except Exception as e:
            # If anything goes wrong, fall back to primary language
            warnings.warn(
                f"Language detection failed for word '{word}': {e}. "
                f"Using primary language '{self.primary_language}'.",
                UserWarning,
                stacklevel=2,
            )
            self._detection_cache[word] = self.primary_language
            return self.primary_language

    def __call__(self, text: str) -> list[GToken]:
        """
        Convert text to tokens with language-aware phonemization.

        Each word is analyzed for its language and routed to the
        appropriate G2P engine. Language information is stored in
        token metadata under 'detected_language'.

        Args:
            text: Input text to phonemize (can contain multiple languages).

        Returns:
            List of GToken objects with phonemes and language metadata.

        Example:
            >>> g2p = MixedLanguageG2P("de", ["de", "en-us"])
            >>> tokens = g2p("Das Meeting ist great!")
            >>> for tok in tokens:
            ...     if tok.is_word:
            ...         lang = tok.get('detected_language')
            ...         print(f"{tok.text} ({lang}): {tok.phonemes}")
        """
        if not text or not text.strip():
            return []

        # Use primary language G2P for initial tokenization
        primary_g2p = self._g2p_instances[self.primary_language]
        tokens = primary_g2p(text)

        # If detection is disabled, just return primary language result
        if not self.enable_detection:
            for token in tokens:
                if token.is_word:
                    token.set("detected_language", self.primary_language)
            return tokens

        # Process each token with language detection
        result_tokens: list[GToken] = []
        for token in tokens:
            if not token.is_word:
                # Keep punctuation/whitespace as-is
                result_tokens.append(token)
                continue

            # Detect word language
            detected_lang = self._detect_word_language(token.text)

            # Store detected language in token metadata
            token.set("detected_language", detected_lang)

            # If detected language differs from primary, re-phonemize
            if detected_lang != self.primary_language:
                g2p = self._g2p_instances[detected_lang]
                # Re-phonemize with detected language
                word_phonemes = g2p.word_to_phonemes(token.text, token.tag)
                if word_phonemes:
                    token.phonemes = word_phonemes
                    # Set rating to 3 (mixed-language, mid-quality)
                    token.set("rating", 3)

            result_tokens.append(token)

        return result_tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """
        Lookup word with automatic language detection.

        Args:
            word: The word to look up.
            tag: Optional POS tag for disambiguation.

        Returns:
            Phoneme string or None if not found.
        """
        detected_lang = self._detect_word_language(word)
        g2p = self._g2p_instances[detected_lang]
        return g2p.lookup(word, tag)

    def clear_detection_cache(self) -> None:
        """Clear the language detection cache.

        Useful when processing very large amounts of text to prevent
        unbounded memory growth.
        """
        self._detection_cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of cached detection results.

        Returns:
            Number of words in the detection cache.
        """
        return len(self._detection_cache)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"MixedLanguageG2P(primary={self.primary_language!r}, "
            f"allowed={self.allowed_languages!r}, "
            f"detection={self.enable_detection})"
        )
