"""Italian G2P (Grapheme-to-Phoneme) converter.

A rule-based Grapheme-to-Phoneme engine for Italian, designed for Kokoro TTS models.

Italian Phonology Features:
- 5 pure vowels (a, e, i, o, u) - always pronounced clearly
- No vowel reduction (unlike English)
- Predictable stress (usually penultimate syllable)
- Gemination (double consonants) is phonemically distinctive
- Palatals: gn [ɲ], gli [ʎ]
- Affricates: z [ʦ/ʣ], c/ci [ʧ], g/gi [ʤ]
- No diphthongs in standard Italian (consecutive vowels are separate syllables)

Reference:
https://en.wikipedia.org/wiki/Italian_phonology
"""

import re
import unicodedata
from typing import Any, Final

from kokorog2p.base import G2PBase
from kokorog2p.it.normalizer import ItalianNormalizer
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

# =============================================================================
# Italian Grapheme-to-Phoneme Mappings
# =============================================================================

# Context-sensitive rules for Italian G2P
# Italian orthography is largely phonemic with predictable rules

# Vowels are straightforward
VOWELS: Final[frozenset[str]] = frozenset("aeiouàèéìòóù")

# Consonants that don't change
SIMPLE_CONSONANTS: Final[dict[str, str]] = {
    "b": "b",
    "d": "d",
    "f": "f",
    "l": "l",
    "m": "m",
    "n": "n",
    "p": "p",
    "r": "r",
    "t": "t",
    "v": "v",
}


class ItalianG2P(G2PBase):
    """Italian G2P converter using rule-based phonemization.

    This class provides grapheme-to-phoneme conversion for Italian text
    using Italian orthographic rules. Italian has fairly regular spelling,
    making rule-based conversion quite accurate.

    Example:
        >>> g2p = ItalianG2P()
        >>> tokens = g2p("Ciao, come stai?")
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

    # Small lexicon for exceptional words or common words with irregular patterns
    _LEXICON = {
        "scusa": "skuʦa",
        "scusi": "skuʦi",
        "poˈ": "poˈ",  # "po'" with stress (preprocessed)
        "gli": "ʎi",  # Article "gli" keeps the 'i'
        "olio": "oljo",  # 'i' is a semivowel [j]
    }

    def __init__(
        self,
        language: str = "it-it",
        use_espeak_fallback: bool = False,
        use_goruut_fallback: bool = False,
        mark_stress: bool = True,
        mark_gemination: bool = True,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        version: str = "1.0",
        **kwargs: Any,
    ) -> None:
        """Initialize the Italian G2P converter.

        Args:
            language: Language code (default: 'it-it').
            use_espeak_fallback: Reserved for future espeak integration.
            mark_stress: Whether to mark primary stress with ˈ.
            mark_gemination: Whether to mark double consonants with ː.
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
        self.mark_gemination = mark_gemination

        # Initialize normalizer
        self._normalizer = ItalianNormalizer(
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

        # Handle specific Italian contractions/abbreviations
        # "po'" (poco) with final apostrophe indicates stress
        text = re.sub(r"\bpo'", "poˈ", text, flags=re.IGNORECASE)

        # Handle Italian contractions with apostrophes
        # c'è -> cè, l'uomo -> luomo, etc.
        # Remove apostrophes that appear between letters
        text = re.sub(r"([a-zA-Zàèéìòóù])'([a-zA-Zàèéìòóù])", r"\1\2", text)

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

    def _process_digraphs(
        self, text: str, i: int, n: int
    ) -> tuple[list[str], int, bool]:
        """Process two-letter graphemes (gn, gli, gl, sc, ch, gh, qu).

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []

        # gn -> ɲ (gnocchi), check for doubling after
        if i + 1 < n and text[i : i + 2] == "gn":
            result.append("ɲ")
            new_i = i + 2
            # Check if followed by another consonant for gemination
            if self.mark_gemination and new_i < n and text[new_i] == "n":
                result.append("ː")
                new_i += 1
            return result, new_i, True

        # gli -> ʎ (famiglia), but only before vowel or word-final
        if i + 2 < n and text[i : i + 3] == "gli":
            if i + 3 >= n or text[i + 3] in VOWELS:
                result.append("ʎ")
                return result, i + 3, True
            # gl before non-vowel -> g + l
            result.append("ɡ")
            return result, i + 1, True

        # gl before i -> ʎ
        if i + 1 < n and text[i : i + 2] == "gl" and i + 2 < n and text[i + 2] == "i":
            result.append("ʎ")
            return result, i + 2, True

        # sc before e/i -> ʃ (pesce)
        if i + 1 < n and text[i : i + 2] == "sc":
            if i + 2 < n and text[i + 2] in "ei":
                result.append("ʃ")
            else:
                # sc before other -> sk
                result.append("s")
                result.append("k")
            return result, i + 2, True

        # ch -> k (che, chi)
        if i + 1 < n and text[i : i + 2] == "ch":
            result.append("k")
            return result, i + 2, True

        # gh -> ɡ (ghetto, ghiro)
        if i + 1 < n and text[i : i + 2] == "gh":
            result.append("ɡ")
            return result, i + 2, True

        # qu -> kw
        if i + 1 < n and text[i : i + 2] == "qu":
            result.append("k")
            result.append("w")
            return result, i + 2, True

        return [], i, False

    def _process_trigraphs(
        self, text: str, i: int, n: int
    ) -> tuple[list[str], int, bool]:
        """Process three-letter graphemes (cqu, cch, ggh) and special uo.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []

        # uo -> wo at word start (uomo -> womo)
        if i == 0 and i + 1 < n and text[i : i + 2] == "uo":
            result.append("w")
            result.append("o")
            return result, i + 2, True

        # cqu -> kːw (acqua)
        if i + 2 < n and text[i : i + 3] == "cqu":
            result.append("k")
            result.append("ː")
            result.append("w")
            return result, i + 3, True

        # cch -> kːk  (occhi)
        if i + 2 < n and text[i : i + 3] == "cch":
            result.append("k")
            result.append("ː")
            return result, i + 2, True

        # ggh -> ɡːɡ (agghiacciare)
        if i + 2 < n and text[i : i + 3] == "ggh":
            result.append("ɡ")
            result.append("ː")
            return result, i + 2, True

        return [], i, False

    def _process_c_consonant(
        self, text: str, i: int, n: int
    ) -> tuple[list[str], int, bool]:
        """Process 'c' with context rules.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []

        # cci/cce -> ʧː (cappuccino)
        if i + 2 < n and text[i : i + 2] == "cc" and text[i + 2] in "ei":
            if self.mark_gemination:
                result.append("ʧ")
                result.append("ː")
                return result, i + 2, True
            result.append("ʧ")
            return result, i + 1, True

        # ci/ce -> ʧ (ciao, cento)
        if i + 1 < n and text[i + 1] in "ei":
            result.append("ʧ")
            return result, i + 1, True

        if i + 1 < n and text[i + 1] == "c":
            # Double c before a/o/u -> k:
            result.append("k")
            result.append("ː")
            return result, i + 2, True

        # c before a/o/u -> k
        result.append("k")
        return result, i + 1, True

    def _process_g_consonant(
        self, text: str, i: int, n: int
    ) -> tuple[list[str], int, bool]:
        """Process 'g' with context rules.

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        result = []

        # ggi/gge -> ʤː (oggi)
        if i + 2 < n and text[i : i + 2] == "gg" and text[i + 2] in "ei":
            new_i = i + 2
            if self.mark_gemination:
                result.append("ʤ")
                result.append("ː")
                # For ggio/ggia, skip the 'i' (formaggio -> formaʤːo)
                if text[new_i] == "i" and new_i + 1 < n and text[new_i + 1] in "aou":
                    new_i += 1
            else:
                result.append("ʤ")
                # For ggio/ggia, skip the 'i' even without gemination
                if text[new_i] == "i" and new_i + 1 < n and text[new_i + 1] in "aou":
                    new_i += 1
            return result, new_i, True

        # gi/ge -> ʤ (giorno, gente)
        if i + 1 < n and text[i + 1] in "ei":
            result.append("ʤ")
            new_i = i + 1
            # Handle 'i' after soft g
            if text[new_i] == "i" and new_i + 1 < n:
                next_char = text[new_i + 1]
                if next_char == "o":
                    # Check if followed by r or n
                    if new_i + 2 < n and text[new_i + 2] in "rn":
                        # Keep the 'i' (giorno, giornale)
                        pass
                    else:
                        # Drop the 'i' (gioca, giocatore)
                        new_i += 1
                elif next_char in "au":
                    # Drop the 'i' (mangia, giulia)
                    new_i += 1
            return result, new_i, True

        if i + 1 < n and text[i + 1] == "g":
            # Double g before a/o/u -> ɡ:
            result.append("ɡ")
            result.append("ː")
            return result, i + 2, True

        # g before a/o/u -> ɡ
        result.append("ɡ")
        return result, i + 1, True

    def _process_simple_chars(
        self, text: str, i: int, n: int, stressed_vowels: set[int]
    ) -> tuple[list[str], int, bool]:
        """Process simple characters (z, h, s, consonants, vowels, j, w, x, y).

        Returns:
            Tuple of (phonemes, new_position, matched).
        """
        char = text[i]
        result = []

        # z -> ʦ or ʣ
        if char == "z":
            if self.mark_gemination and i + 1 < n and text[i + 1] == "z":
                result.append("ʦ")
                result.append("ː")
                return result, i + 2, True
            result.append("ʦ")
            return result, i + 1, True

        # h is silent
        if char == "h":
            return result, i + 1, True

        # s -> s
        if char == "s":
            if self.mark_gemination and i + 1 < n and text[i + 1] == "s":
                result.append("s")
                result.append("ː")
                return result, i + 2, True
            result.append("s")
            return result, i + 1, True

        # Simple consonants
        if char in SIMPLE_CONSONANTS:
            consonant = SIMPLE_CONSONANTS[char]
            if self.mark_gemination and i + 1 < n and text[i + 1] == char:
                result.append(consonant)
                result.append("ː")
                return result, i + 2, True
            result.append(consonant)
            return result, i + 1, True

        # Vowels
        if char in "aeiou":
            result.append(char)
            if self.mark_stress and i in stressed_vowels:
                result.append("ˈ")
            return result, i + 1, True

        # j -> j (semivowel)
        if char == "j":
            result.append("j")
            return result, i + 1, True

        # w -> w (in loan words)
        if char == "w":
            result.append("w")
            return result, i + 1, True

        # x -> ks (in loan words)
        if char == "x":
            result.append("k")
            result.append("s")
            return result, i + 1, True

        # y -> i (in loan words)
        if char == "y":
            result.append("i")
            return result, i + 1, True

        return [], i, False

    def _word_to_phonemes(self, word: str) -> str:
        """Convert a single word to phonemes using Italian rules.

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
            # Apply stress and gemination markers if needed
            if not self.mark_stress:
                base_phonemes = base_phonemes.replace("ˈ", "")
            if not self.mark_gemination:
                base_phonemes = base_phonemes.replace("ː", "")
            return base_phonemes

        # Convert to lowercase for processing
        text = word.lower()

        # Find stressed vowels before normalization
        stressed_vowels = set()
        normalized_text: list[str] = []
        for _i, char in enumerate(text):
            if char in "àèéìòóù":
                # Remember the position of the normalized vowel
                stressed_vowels.add(len(normalized_text))
                # Normalize the accented vowel
                if char == "à":
                    normalized_text.append("a")
                elif char in "èé":
                    normalized_text.append("e")
                elif char == "ì":
                    normalized_text.append("i")
                elif char in "òó":
                    normalized_text.append("o")
                elif char == "ù":
                    normalized_text.append("u")
            else:
                normalized_text.append(char)

        text = "".join(normalized_text)

        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            matched = False

            # Try trigraphs first (uo, cqu, cch, ggh)
            phonemes, new_i, was_matched = self._process_trigraphs(text, i, n)
            if was_matched:
                result.extend(phonemes)
                i = new_i
                matched = True

            # Try digraphs (gn, gli, gl, sc, ch, gh, qu)
            if not matched:
                phonemes, new_i, was_matched = self._process_digraphs(text, i, n)
                if was_matched:
                    result.extend(phonemes)
                    i = new_i
                    matched = True

            # Process 'c' with context
            if not matched and text[i] == "c":
                phonemes, new_i, was_matched = self._process_c_consonant(text, i, n)
                result.extend(phonemes)
                i = new_i
                matched = True

            # Process 'g' with context
            if not matched and text[i] == "g":
                phonemes, new_i, was_matched = self._process_g_consonant(text, i, n)
                result.extend(phonemes)
                i = new_i
                matched = True

            # Process simple characters (z, h, s, consonants, vowels, j, w, x, y)
            if not matched:
                phonemes, new_i, was_matched = self._process_simple_chars(
                    text, i, n, stressed_vowels
                )
                if was_matched:
                    result.extend(phonemes)
                    i = new_i
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
            tag: Optional POS tag (ignored for Italian).

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
        return f"ItalianG2P(language={self.language!r}, version={self.version!r})"

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
