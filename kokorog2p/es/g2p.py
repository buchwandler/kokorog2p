"""Spanish G2P (Grapheme-to-Phoneme) converter.

A rule-based Grapheme-to-Phoneme engine for Spanish, designed for Kokoro TTS models.

Spanish Phonology Features:
- 5 pure vowels (a, e, i, o, u) - always pronounced clearly
- No vowel reduction (unlike English)
- Predictable stress (penultimate for vowel-ending words, final for consonant-ending)
- Palatal sounds: ñ [ɲ], ll [ʎ] (or [j] in most dialects), ch [ʧ]
- Jota: j/g+e/i [x]
- Theta: z/c+e/i [θ] in European Spanish (or [s] in Latin America)
- Tap vs trill: r [ɾ] vs rr/initial r [r]
- No consonant clusters simplification

Reference:
https://en.wikipedia.org/wiki/Spanish_phonology
"""

import re
import unicodedata
from typing import Any, Final

from kokorog2p.base import G2PBase
from kokorog2p.es.normalizer import SpanishNormalizer
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

# =============================================================================
# Spanish Grapheme-to-Phoneme Mappings
# =============================================================================

# Vowels are straightforward
VOWELS: Final[frozenset[str]] = frozenset("aeiouáéíóú")

# Simple consonants that don't change
SIMPLE_CONSONANTS: Final[dict[str, str]] = {
    "f": "f",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "p": "p",
    "s": "s",
    "t": "t",
}


class SpanishG2P(G2PBase):
    """Spanish G2P converter using rule-based phonemization.

    This class provides grapheme-to-phoneme conversion for Spanish text
    using Spanish orthographic rules. Spanish has fairly regular spelling,
    making rule-based conversion quite accurate.

    Example:
        >>> g2p = SpanishG2P()
        >>> tokens = g2p("Hola, ¿cómo estás?")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    # Punctuation normalization map
    _PUNCT_MAP = {
        chr(171): '"',  # «
        chr(187): '"',  # »
        chr(8216): "'",  # '
        chr(8217): "'",  # '
        chr(8220): '"',  # "
        chr(8221): '"',  # "
        chr(8212): "-",  # —
        chr(8211): "-",  # –
        chr(8230): "...",  # …
        "¿": "?",  # Inverted question mark
        "¡": "!",  # Inverted exclamation mark
    }

    # Small lexicon for exceptional words or common words with irregular patterns
    _LEXICON: dict[str, str] = {
        # Conjunction "y" (and) is always pronounced as [i]
        "y": "i",
        # "hacer" and derivatives use [s] not [θ] even in European Spanish
        "hacer": "aseɾ",
        # Common words with predictable stress
        "excelente": "ekseˈlente",
        # Add other exceptions as needed
    }

    def __init__(
        self,
        language: str = "es",
        use_espeak_fallback: bool = False,
        use_goruut_fallback: bool = False,
        mark_stress: bool = True,
        dialect: str = "es",  # "es" for European, "la" for Latin American
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        version: str = "1.0",
        **kwargs: Any,
    ) -> None:
        """Initialize the Spanish G2P converter.

        Args:
            language: Language code (default: 'es').
            use_espeak_fallback: Reserved for future espeak integration.
            use_goruut_fallback: Reserved for future goruut integration.
            mark_stress: Whether to mark primary stress with ˈ.
            dialect: "es" for European Spanish (with θ), "la" for Latin American (θ→s).
            expand_abbreviations: Whether to expand common abbreviations.
            enable_context_detection: Context-aware abbreviation expansion.
            version: Target model version.
        """
        super().__init__(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
        )
        self.version = version
        self.mark_stress = mark_stress
        self.dialect = dialect

        # Initialize normalizer
        self._normalizer = SpanishNormalizer(
            expand_abbreviations=expand_abbreviations,
            enable_context_detection=enable_context_detection,
        )

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        if not text.strip():
            return []

        # Preprocess
        text = self._preprocess(text)

        # Tokenize
        tokens = self._tokenize(text)

        # Process tokens
        for token in tokens:
            # Skip tokens that already have phonemes (punctuation)
            if token.phonemes is not None:
                continue

            # Convert word to phonemes
            if token.is_word:
                phonemes = self._word_to_phonemes(token.text)
                if phonemes:
                    token.phonemes = phonemes
                    token.set("rating", 3)  # Rule-based rating

        # Handle remaining unknown words
        for token in tokens:
            if token.phonemes is None and token.is_word:
                token.phonemes = "?"

        ensure_gtoken_positions(tokens, text)
        return tokens

    def _preprocess(self, text: str) -> str:
        """Preprocess text before G2P conversion.

        Args:
            text: Raw input text.

        Returns:
            Preprocessed text.
        """
        # Normalize Unicode
        text = unicodedata.normalize("NFC", text)

        # Apply normalizer (abbreviations, temperature, etc.)
        text = self._normalizer(text)

        # Normalize punctuation (keep for legacy compatibility)
        for old, new in self._PUNCT_MAP.items():
            text = text.replace(old, new)

        # Remove non-breaking spaces
        text = text.replace("\u00a0", " ")
        text = text.replace("\u202f", " ")

        # Collapse multiple spaces
        text = re.sub(r" +", " ", text)

        return text.strip()

    def _tokenize(self, text: str) -> list[GToken]:
        """Tokenize text into words and punctuation.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        tokens: list[GToken] = []

        # Simple word/punct split
        for match in re.finditer(r"(\w+|[^\w\s]+|\s+)", text, re.UNICODE):
            word = match.group()
            if word.isspace():
                if tokens:
                    tokens[-1].whitespace = word
                continue

            token = GToken(text=word, tag="", whitespace="")

            # Handle punctuation
            if not any(c.isalnum() for c in word):
                token.phonemes = self._get_punct_phonemes(word)
                token.set("rating", 4)

            tokens.append(token)

        return tokens

    @staticmethod
    def _get_punct_phonemes(text: str) -> str:
        """Get phonemes for punctuation tokens."""
        # Keep common punctuation
        puncts = frozenset(";:,.!?-\"'()[]—…")
        return "".join("—" if c == "-" else c for c in text if c in puncts)

    def _process_multi_char_sequences(
        self, text: str, i: int, n: int
    ) -> tuple[list[str], int, bool]:
        """Process multi-character grapheme sequences.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []

        # ch -> ʧ (chico)
        if i + 1 < n and text[i : i + 2] == "ch":
            result.append("ʧ")
            return result, i + 2, True

        # ll -> ʎ or j depending on dialect (most use j, some use ʎ)
        # For now, use ʎ for traditional pronunciation
        if i + 1 < n and text[i : i + 2] == "ll":
            result.append("ʎ")
            return result, i + 2, True

        # rr -> r (trill)
        if i + 1 < n and text[i : i + 2] == "rr":
            result.append("r")
            return result, i + 2, True

        # qu + e/i -> k (queso, quien)
        if i + 2 < n and text[i : i + 2] == "qu" and text[i + 2] in "ei":
            result.append("k")
            return result, i + 2, True

        # gu + e/i -> ɡ (guerra, guiso)
        if i + 2 < n and text[i : i + 2] == "gu" and text[i + 2] in "ei":
            result.append("ɡ")
            return result, i + 2, True

        # gü + e/i -> ɡw (güero, pingüino)
        if i + 2 < n and text[i : i + 3] == "gü" and i + 3 < n and text[i + 3] in "ei":
            result.append("ɡ")
            result.append("w")
            return result, i + 2, True

        return [], i, False

    def _process_context_consonants(
        self, text: str, i: int, n: int, result: list[str]
    ) -> tuple[list[str], int, bool]:
        """Process consonants with context-dependent rules (c, z, g, j, h, x, r).

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        char = text[i]
        phonemes = []

        # ñ -> ɲ (niño)
        if char == "ñ":
            phonemes.append("ɲ")
            return phonemes, i + 1, True

        # c before e/i -> θ (in European Spanish) or s (in Latin American)
        # Exception: after x (as in excelente), use s
        if char == "c":
            if i + 1 < n and text[i + 1] in "ei":
                # Check if previous phoneme is 's' (from 'x' -> 'ks')
                if result and result[-1] == "s":
                    # After x, use s: excelente → ekselente
                    phonemes.append("s")
                elif self.dialect == "es":
                    phonemes.append("θ")
                else:
                    phonemes.append("s")
            else:
                # c before a/o/u -> k
                phonemes.append("k")
            return phonemes, i + 1, True

        # z -> θ (in European Spanish) or s (in Latin American)
        if char == "z":
            if self.dialect == "es":
                phonemes.append("θ")
            else:
                phonemes.append("s")
            return phonemes, i + 1, True

        # g before e/i -> x (jota sound)
        if char == "g":
            if i + 1 < n and text[i + 1] in "ei":
                phonemes.append("x")
            else:
                # g before a/o/u -> ɡ
                phonemes.append("ɡ")
            return phonemes, i + 1, True

        # j -> x (jota)
        if char == "j":
            phonemes.append("x")
            return phonemes, i + 1, True

        # h is silent
        if char == "h":
            return phonemes, i + 1, True

        # x -> ks (except in Mexican Spanish where it can be [x])
        # Special case: xc before e/i -> ks (not ksθ/kss)
        if char == "x":
            phonemes.append("k")
            phonemes.append("s")
            # Skip following 'c' if it comes before e/i (excelente → ekselente)
            if i + 1 < n and text[i + 1] == "c" and i + 2 < n and text[i + 2] in "ei":
                return phonemes, i + 2, True
            return phonemes, i + 1, True

        # r -> ɾ (tap) or r (trill at word start or after n/l/s)
        if char == "r":
            # Trill at word start or after n, l, s
            if i == 0 or (i > 0 and text[i - 1] in "nls"):
                phonemes.append("r")
            else:
                phonemes.append("ɾ")
            return phonemes, i + 1, True

        return [], i, False

    def _process_simple_consonants(
        self, text: str, i: int, n: int
    ) -> tuple[list[str], int, bool]:
        """Process simple consonants (b, v, d, w, y, and SIMPLE_CONSONANTS).

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        char = text[i]
        phonemes = []

        # b/v -> b (they're the same phoneme in Spanish)
        if char in "bv":
            phonemes.append("b")
            return phonemes, i + 1, True

        # d -> d
        if char == "d":
            phonemes.append("d")
            return phonemes, i + 1, True

        # Simple consonants
        if char in SIMPLE_CONSONANTS:
            phonemes.append(SIMPLE_CONSONANTS[char])
            return phonemes, i + 1, True

        # w -> w (in loanwords)
        if char == "w":
            phonemes.append("w")
            return phonemes, i + 1, True

        # y -> j (consonantal y) or i (vowel in diphthongs)
        if char == "y":
            # At start of word or syllable, it's consonantal [j]: yo, ayer
            # Between vowels or at end, check context
            if i == 0:
                # Word-initial: yo → jo
                phonemes.append("j")
            elif i == n - 1:
                # Word-final: muy, soy, hoy → i
                phonemes.append("i")
            elif i + 1 < n and text[i + 1] in "aeiou":
                # Before vowel: ayer → ajer (consonantal)
                phonemes.append("j")
            else:
                # Default: use i for conjunction and word-final position
                phonemes.append("i")
            return phonemes, i + 1, True

        return [], i, False

    def _word_to_phonemes(self, word: str) -> str:
        """Convert a single word to phonemes using Spanish rules.

        Args:
            word: Word to convert.

        Returns:
            Phoneme string in IPA.
        """
        if not word:
            return ""

        # Check lexicon first for exceptional words
        word_lower = word.lower()
        if word_lower in self._LEXICON:
            base_phonemes = self._LEXICON[word_lower]
            # Apply stress markers if needed
            if not self.mark_stress:
                base_phonemes = base_phonemes.replace("ˈ", "")
            return base_phonemes

        # Convert to lowercase for processing
        text = word.lower()

        # Find stressed vowels before normalization
        stressed_vowels = set()
        normalized_text: list[str] = []
        for _i, char in enumerate(text):
            if char in "áéíóú":
                # Remember the position of the normalized vowel
                stressed_vowels.add(len(normalized_text))
                # Normalize the accented vowel
                if char == "á":
                    normalized_text.append("a")
                elif char == "é":
                    normalized_text.append("e")
                elif char == "í":
                    normalized_text.append("i")
                elif char == "ó":
                    normalized_text.append("o")
                elif char == "ú":
                    normalized_text.append("u")
            else:
                normalized_text.append(char)

        text = "".join(normalized_text)

        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            matched = False

            # Try multi-character sequences first
            phonemes, new_i, was_matched = self._process_multi_char_sequences(
                text, i, n
            )
            if was_matched:
                result.extend(phonemes)
                i = new_i
                matched = True

            # Try context consonants (c, z, g, j, h, x, r)
            if not matched:
                phonemes, new_i, was_matched = self._process_context_consonants(
                    text, i, n, result
                )
                if was_matched:
                    result.extend(phonemes)
                    i = new_i
                    matched = True

            # Try simple consonants (b, v, d, w, y, etc.)
            if not matched:
                phonemes, new_i, was_matched = self._process_simple_consonants(
                    text, i, n
                )
                if was_matched:
                    result.extend(phonemes)
                    i = new_i
                    matched = True

            # Vowels
            if not matched and text[i] in "aeiou":
                vowel = text[i]
                result.append(vowel)
                # Add stress mark AFTER the vowel if this vowel is stressed
                if self.mark_stress and i in stressed_vowels:
                    result.append("ˈ")
                i += 1
                matched = True

            # Unknown character
            if not matched:
                # Skip unknown characters
                i += 1

        return "".join(result)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word's phonemes.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for Spanish).

        Returns:
            Phoneme string or None.
        """
        return self._word_to_phonemes(word)

    def phonemize(self, text: str) -> str:
        """Convert text to phonemes.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string.
        """
        tokens = self(text)
        result = []
        for token in tokens:
            if token.phonemes:
                result.append(token.phonemes)
                if token.whitespace:
                    result.append(token.whitespace)
        return "".join(result).rstrip()

    def __repr__(self) -> str:
        return (
            f"SpanishG2P(language={self.language!r}, "
            f" dialect={self.dialect!r}, version={self.version!r})"
        )

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
