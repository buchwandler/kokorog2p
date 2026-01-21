"""Brazilian Portuguese G2P (Grapheme-to-Phoneme) converter.

A rule-based Grapheme-to-Phoneme engine for Brazilian Portuguese,
designed for Kokoro TTS.

Brazilian Portuguese Phonology Features:
- 7 oral vowels (a, e, ɛ, i, o, ɔ, u) with open/closed e/o variants
- 5 nasal vowels (ã, ẽ, ĩ, õ, ũ)
- Nasal diphthongs (ãw̃, õj̃, etc.)
- Palatalization: lh [ʎ], nh [ɲ], x/ch [ʃ]
- Affrication: t+i [ʧ], d+i [ʤ] (Brazilian Portuguese feature)
- Sibilants: s [s/z], x [ʃ], z [z]
- Liquids: r [ʁ/x/h] (varies by dialect), rr [ʁ/x], single r [ɾ]
- No θ sound (unlike European Portuguese)

Reference:
https://en.wikipedia.org/wiki/Portuguese_phonology
https://en.wikipedia.org/wiki/Brazilian_Portuguese
"""

import re
import unicodedata
from typing import Any, Final

from kokorog2p.base import G2PBase
from kokorog2p.pt.normalizer import PortugueseNormalizer
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

# =============================================================================
# Brazilian Portuguese Grapheme-to-Phoneme Mappings
# =============================================================================

# Oral vowels (7 vowels in stressed position)
ORAL_VOWELS: Final[frozenset[str]] = frozenset("aeiouɛɔ")

# Vowels that can be nasalized
NASAL_VOWELS: Final[str] = "aeiou"

# Simple consonants that don't change much
SIMPLE_CONSONANTS: Final[dict[str, str]] = {
    "b": "b",
    "f": "f",
    "k": "k",
    "p": "p",
    "v": "v",
}


class PortugueseG2P(G2PBase):
    """Brazilian Portuguese G2P converter using rule-based phonemization.

    This class provides grapheme-to-phoneme conversion for Brazilian Portuguese text
    using Portuguese orthographic rules.

    Example:
        >>> g2p = PortugueseG2P()
        >>> tokens = g2p("Olá, como está?")
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
    }

    # Small lexicon for exceptional words
    _LEXICON: dict[str, str] = {
        # Common words
        "e": "i",  # Conjunction "and"
        "é": "ɛˈ",  # "is" (stressed open e)
        # Add more as needed
    }

    def __init__(
        self,
        language: str = "pt-br",
        use_espeak_fallback: bool = False,
        mark_stress: bool = True,
        affricate_ti_di: bool = True,  # Affricate t/d before i (Brazilian feature)
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        dialect: str = "br",  # "br" for Brazilian, "pt" for European
        version: str = "1.0",
        **kwargs: Any,
    ) -> None:
        """Initialize the Portuguese G2P converter.

        Args:
            language: Language code (default: 'pt-br').
            use_espeak_fallback: Reserved for future espeak integration.
            mark_stress: Whether to mark primary stress with ˈ.
            affricate_ti_di: Whether to affricate /t d/ before /i/ (Brazilian feature).
            expand_abbreviations: Whether to expand common abbreviations.
            enable_context_detection: Context-aware abbreviation expansion.
            dialect: "br" for Brazilian, "pt" for European Portuguese.
                     Affects number pronunciation (dezesseis vs dezasseis)
            version: Target model version.
        """
        super().__init__(language=language, use_espeak_fallback=use_espeak_fallback)
        self.version = version
        self.mark_stress = mark_stress
        self.affricate_ti_di = affricate_ti_di
        self.dialect = dialect

        # Initialize normalizer with dialect support
        self._normalizer = PortugueseNormalizer(
            expand_abbreviations=expand_abbreviations,
            enable_context_detection=enable_context_detection,
            dialect=dialect,
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
            text: Preprocessed text.

        Returns:
            List of GToken objects.
        """
        # Pattern to split on whitespace and capture punctuation
        pattern = r"([^\w'-]+|[\w'-]+)"
        parts = re.findall(pattern, text)

        tokens = []
        for part in parts:
            if not part or part.isspace():
                continue

            # Check if it's a word or punctuation
            if re.match(r"[\w'-]+", part):
                # It's a word
                token = GToken(text=part)
                token.set("is_word", True)
                tokens.append(token)
            else:
                # It's punctuation
                token = GToken(text=part)
                token.set("is_word", False)
                token.phonemes = part  # Punctuation passes through
                tokens.append(token)

        return tokens

    def _normalize_text(self, text: str) -> tuple[str, set[int], set[int]]:
        """Normalize accented characters and track stress positions.

        Args:
            text: Input text with possible accents.

        Returns:
            Tuple of (normalized_text, stressed_vowel_positions,
            open_vowel_positions).
        """
        stressed_vowels = set()
        open_vowels = set()  # Track é/ó (open) vs ê/ô (closed)
        normalized_text: list[str] = []

        for _i, char in enumerate(text):
            if char in "áéíóúâêôãõ":
                # Remember position
                pos = len(normalized_text)
                stressed_vowels.add(pos)
                # Track open vowels (acute accent)
                if char in "éó":
                    open_vowels.add(pos)
                # Normalize
                if char == "á":
                    normalized_text.append("a")
                elif char in ("é", "ê"):
                    normalized_text.append("e")
                elif char == "í":
                    normalized_text.append("i")
                elif char in ("ó", "ô"):
                    normalized_text.append("o")
                elif char == "ú":
                    normalized_text.append("u")
                elif char in ("ã", "õ"):
                    # Keep tilde for later
                    normalized_text.append(char)
            else:
                normalized_text.append(char)

        return "".join(normalized_text), stressed_vowels, open_vowels

    def _process_vowel(
        self,
        text: str,
        i: int,
        n: int,
        stressed_vowels: set[int],
        open_vowels: set[int],
    ) -> tuple[list[str], int]:
        """Process a vowel and possible diphthong.

        Args:
            text: Normalized text.
            i: Current position.
            n: Text length.
            stressed_vowels: Set of stressed vowel positions.
            open_vowels: Set of open vowel positions.

        Returns:
            Tuple of (phonemes, new_position).
        """
        vowel = text[i]
        result = []

        if vowel == "e":
            # Use open ɛ only if stressed AND has acute accent (é)
            if i in stressed_vowels and i in open_vowels:
                result.append("ɛ")
            else:
                result.append("e")
            # Check for eu diphthong -> ew (meu, seu)
            if i + 1 < n and text[i + 1] == "u":
                result.append("w")
                i += 1

        elif vowel == "o":
            # Use open ɔ only if stressed AND has acute accent (ó)
            if i in stressed_vowels and i in open_vowels:
                result.append("ɔ")
            else:
                result.append("o")
            # Check for ou diphthong -> ow (vou, sou)
            if i + 1 < n and text[i + 1] == "u":
                result.append("w")
                i += 1

        elif vowel == "u":
            result.append("u")
            # Check for ui diphthong -> uj (muito)
            if i + 1 < n and text[i + 1] == "i":
                result.append("j")
                i += 1

        elif vowel == "a":
            result.append("a")
            # Check for au diphthong -> aw (Tchau, mau)
            if i + 1 < n and text[i + 1] == "u":
                result.append("w")
                i += 1

        elif vowel == "i":
            result.append("i")

        # Add stress marker if applicable
        if self.mark_stress and i in stressed_vowels:
            result.append("ˈ")

        return result, i + 1

    def _process_t_consonant(
        self, text: str, i: int, n: int, stressed_vowels: set[int]
    ) -> tuple[list[str], int, bool]:
        """Process 't' consonant with possible affrication.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []
        matched = False

        if self.affricate_ti_di:
            # Final "te" -> ʧi
            if (
                i + 1 < n
                and text[i + 1] == "e"
                and (i + 1) not in stressed_vowels
                and i + 2 >= n
            ):
                result.extend(["ʧ", "i"])
                return result, i + 2, True
            # t + i (unstressed) -> ʧ
            if i + 1 < n and text[i + 1] == "i" and (i + 1) not in stressed_vowels:
                result.append("ʧ")
                return result, i + 1, True

        result.append("t")
        return result, i + 1, matched

    def _process_d_consonant(
        self, text: str, i: int, n: int, stressed_vowels: set[int]
    ) -> tuple[list[str], int, bool]:
        """Process 'd' consonant with possible affrication.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []
        matched = False

        if self.affricate_ti_di:
            # d + i (unstressed) -> ʤ
            if i + 1 < n and text[i + 1] == "i" and (i + 1) not in stressed_vowels:
                result.append("ʤ")
                return result, i + 1, True

        result.append("d")
        return result, i + 1, matched

    def _process_nasal_vowel(
        self, text: str, i: int, n: int, stressed_vowels: set[int]
    ) -> tuple[list[str], int, bool]:
        """Process nasal vowel combination.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        if not (
            i + 1 < n
            and text[i] in NASAL_VOWELS
            and text[i + 1] in "mn"
            and (i + 2 >= n or text[i + 2] not in "aeiouãõh")
        ):
            return [], i, False

        result = []
        vowel = text[i]

        # Nasalize vowel
        nasal_map = {"a": "ã", "e": "ẽ", "i": "ĩ", "o": "õ", "u": "ũ"}
        if vowel in nasal_map:
            result.append(nasal_map[vowel])

        # Add stress if needed
        if self.mark_stress and i in stressed_vowels:
            result.append("ˈ")

        # Add nasal consonant
        result.append(text[i + 1])

        return result, i + 2, True

    def _process_multi_char_sequences(
        self, text: str, i: int, n: int
    ) -> tuple[list[str], int, bool]:
        """Process multi-character grapheme sequences.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []

        # tch -> ʧ (Tchau, tchau)
        if i + 2 < n and text[i : i + 3] == "tch":
            result.append("ʧ")
            return result, i + 3, True

        # nh -> ɲ (ninho)
        if i + 1 < n and text[i : i + 2] == "nh":
            result.append("ɲ")
            return result, i + 2, True

        # lh -> ʎ (filho)
        if i + 1 < n and text[i : i + 2] == "lh":
            result.append("ʎ")
            return result, i + 2, True

        # ch -> ʃ (chá)
        if i + 1 < n and text[i : i + 2] == "ch":
            result.append("ʃ")
            return result, i + 2, True

        # rr -> r or ʁ (strong r: carro)
        if i + 1 < n and text[i : i + 2] == "rr":
            result.append("r")  # Use r for strong trill
            return result, i + 2, True

        # ss -> s (isso -> iso)
        if i + 1 < n and text[i : i + 2] == "ss":
            result.append("s")
            return result, i + 2, True

        # qu + vowel -> kw or k
        if i + 2 < n and text[i : i + 2] == "qu":
            if text[i + 2] in "ei":
                result.append("k")
            else:
                result.append("k")
                result.append("w")
            return result, i + 2, True

        # gu + vowel -> ɡw or ɡ
        if i + 2 < n and text[i : i + 2] == "gu":
            if text[i + 2] in "ei":
                result.append("ɡ")
            else:
                result.append("ɡ")
                result.append("w")
            return result, i + 2, True

        return [], i, False

    def _process_simple_consonants(
        self, text: str, i: int, n: int, stressed_vowels: set[int]
    ) -> tuple[list[str], int, bool]:
        """Process simple consonants with context rules.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        char = text[i]
        result = []

        # Simple consonants (b, f, k, p, v)
        if char in SIMPLE_CONSONANTS:
            result.append(SIMPLE_CONSONANTS[char])
            return result, i + 1, True

        # c: before e/i -> s, otherwise k
        if char == "c":
            if i + 1 < n and text[i + 1] in "ei":
                result.append("s")
            else:
                result.append("k")
            return result, i + 1, True

        # ç -> s
        if char == "ç":
            result.append("s")
            return result, i + 1, True

        # g: before e/i -> ʒ, otherwise ɡ
        if char == "g":
            if i + 1 < n and text[i + 1] in "ei":
                result.append("ʒ")
            else:
                result.append("ɡ")
            return result, i + 1, True

        # j -> ʒ
        if char == "j":
            result.append("ʒ")
            return result, i + 1, True

        # x -> ʃ
        if char == "x":
            result.append("ʃ")
            return result, i + 1, True

        # z: final -> s, otherwise z
        if char == "z":
            if i + 1 >= n:
                result.append("s")
            else:
                result.append("z")
            return result, i + 1, True

        # s: between vowels -> z, otherwise s
        if char == "s":
            if (
                i > 0
                and i + 1 < n
                and text[i - 1] in "aeiouãõ"
                and text[i + 1] in "aeiouãõ"
            ):
                result.append("z")
            else:
                result.append("s")
            return result, i + 1, True

        # r: initial -> r, otherwise ɾ
        if char == "r":
            if i == 0:
                result.append("r")
            else:
                result.append("ɾ")
            return result, i + 1, True

        # l: before consonant/final -> w, otherwise l
        if char == "l":
            if i + 1 >= n or text[i + 1] not in "aeiouãõ":
                result.append("w")
            else:
                result.append("l")
            return result, i + 1, True

        # m, n -> pass through
        if char in "mn":
            result.append(char)
            return result, i + 1, True

        # w, y -> w, j
        if char in "wy":
            if char == "w":
                result.append("w")
            else:
                result.append("j")
            return result, i + 1, True

        return [], i, False

    def _word_to_phonemes(self, word: str) -> str:
        """Convert a single word to phonemes.

        Args:
            word: Word to convert.

        Returns:
            Phoneme string in IPA.
        """
        if not word:
            return ""

        # Check lexicon first
        word_lower = word.lower()
        if word_lower in self._LEXICON:
            base_phonemes = self._LEXICON[word_lower]
            if not self.mark_stress:
                base_phonemes = base_phonemes.replace("ˈ", "")
            return base_phonemes

        # Convert to lowercase for processing
        text = word.lower()

        # Normalize and track stress
        text, stressed_vowels, open_vowels = self._normalize_text(text)

        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            matched = False

            # Multi-character sequences first
            phonemes, new_i, was_matched = self._process_multi_char_sequences(
                text, i, n
            )
            if was_matched:
                result.extend(phonemes)
                i = new_i
                matched = True

            # Try nasal combinations if not yet matched
            if not matched:
                phonemes, new_i, was_matched = self._process_nasal_vowel(
                    text, i, n, stressed_vowels
                )
                if was_matched:
                    result.extend(phonemes)
                    i = new_i
                    matched = True

            # Already-nasalized vowels
            if not matched and text[i] in "ãõ":
                result.append(text[i])
                if self.mark_stress and i in stressed_vowels:
                    result.append("ˈ")
                i += 1
                matched = True

            # t/d consonants with affrication
            if not matched and text[i] == "t":
                phonemes, new_i, was_matched = self._process_t_consonant(
                    text, i, n, stressed_vowels
                )
                result.extend(phonemes)
                i = new_i
                matched = True

            if not matched and text[i] == "d":
                phonemes, new_i, was_matched = self._process_d_consonant(
                    text, i, n, stressed_vowels
                )
                result.extend(phonemes)
                i = new_i
                matched = True

            # Other consonants
            if not matched:
                phonemes, new_i, was_matched = self._process_simple_consonants(
                    text, i, n, stressed_vowels
                )
                if was_matched:
                    result.extend(phonemes)
                    i = new_i
                    matched = True

            # Vowels (with possible diphthongs)
            if not matched and text[i] in "aeiou":
                phonemes, new_i = self._process_vowel(
                    text, i, n, stressed_vowels, open_vowels
                )
                result.extend(phonemes)
                i = new_i
                matched = True

            # Unknown character - skip
            if not matched:
                i += 1

        return "".join(result)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word's phonemes.

        Args:
            word: The word to look up.
            tag: Optional POS tag (ignored for Portuguese).

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
        return " ".join(result)

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
