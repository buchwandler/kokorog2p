"""German G2P (Grapheme-to-Phoneme) converter.

Grapheme to Phoneme for German language using dictionary lookup
with rule-based fallback.

German Phonology features:
- Final obstruent devoicing (Auslautverhärtung)
- Vowel length distinction
- Umlauts (ä, ö, ü)
- ß (Eszett)
- CH as [ç] or [x] depending on context (ich-Laut vs ach-Laut)
- Voicing assimilation in consonant clusters
- Schwa in unstressed syllables

Reference:
https://en.wikipedia.org/wiki/Standard_German_phonology
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final

from kokorog2p.base import G2PBase
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

if TYPE_CHECKING:
    from kokorog2p.de.lexicon import GermanLexicon

# =============================================================================
# German Phoneme Mappings
# =============================================================================

# Basic IPA mappings for German graphemes
# Note: Many mappings are context-dependent and handled by rules
IPA: Final[dict[str, str]] = {
    # Vowels - short
    "a": "a",
    "e": "ɛ",
    "i": "ɪ",
    "o": "ɔ",
    "u": "ʊ",
    "ä": "ɛ",
    "ö": "œ",
    "ü": "ʏ",
    "y": "ʏ",
    # Vowels - long (marked with doubling or followed by h/single consonant)
    "aa": "aː",
    "ee": "eː",
    "ie": "iː",
    "oo": "oː",
    "uh": "uː",
    "äh": "ɛː",
    "öh": "øː",
    "üh": "yː",
    "ah": "aː",
    "eh": "eː",
    "ih": "iː",
    "oh": "oː",
    # Diphthongs
    "ei": "aɪ",
    "ai": "aɪ",
    "ey": "aɪ",
    "ay": "aɪ",
    "au": "aʊ",
    "eu": "ɔʏ",
    "äu": "ɔʏ",
    # Consonants
    "b": "b",
    "c": "k",
    "d": "d",
    "f": "f",
    "g": "ɡ",
    "h": "h",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "p": "p",
    "q": "k",
    "r": "ʁ",
    "s": "z",  # Default voiced, devoiced in certain contexts
    "t": "t",
    "v": "f",  # Usually [f] in German
    "w": "v",
    "x": "ks",
    "z": "ʦ",
    "ß": "s",
    # Digraphs and trigraphs
    "ch": "x",  # Default ach-Laut, ich-Laut handled by rule
    "ck": "k",
    "dt": "t",
    "ng": "ŋ",
    "nk": "ŋk",
    "ph": "f",
    "pf": "pf",
    "qu": "kv",
    "sch": "ʃ",
    "sp": "ʃp",  # Word-initial
    "st": "ʃt",  # Word-initial
    "ss": "s",
    "th": "t",
    "tz": "ʦ",
    "tsch": "ʧ",
    "dsch": "ʤ",
    "chs": "ks",
}

# Voiced-unvoiced consonant pairs for final devoicing
VOICED_TO_UNVOICED: Final[dict[str, str]] = {
    "b": "p",
    "d": "t",
    "g": "k",
    "ɡ": "k",  # IPA g (U+0261)
    "v": "f",
    "z": "s",
    "ʒ": "ʃ",
}


def _is_front_vowel_context(prev_chars: str) -> bool:
    """Check if the previous character(s) form a front vowel context for ich-Laut."""
    prev_lower = prev_chars.lower()
    # Check for front vowels and consonants l, n, r
    if prev_lower in ("i", "e", "ä", "ö", "ü", "y"):
        return True
    if prev_lower in ("l", "n", "r"):
        return True
    # Check for diphthongs ending in front vowel
    if prev_lower.endswith(("ei", "ai", "eu", "äu", "ie", "ey", "ay")):
        return True
    return False


def normalize_to_kokoro(phonemes: str, use_tie_replacement: bool = False) -> str:
    """Normalize German phonemes to Kokoro-compatible format.

    Converts combining diacritics to precomposed characters that exist
    in the Kokoro TTS vocabulary.

    Args:
        phonemes: IPA phoneme string potentially containing combining diacritics.
        use_tie_replacement: If True, replace tie characters (͡) with special
        phonmes. Default is False.

    Returns:
        Normalized phoneme string compatible with Kokoro vocab.
    """
    if not phonemes:
        return phonemes
    # Replace tie characters (U+0361) with special phonemes if requested
    if use_tie_replacement:
        phonemes = phonemes.replace("͡", "^")
        phonemes = phonemes.replace("a^ɪ", "I")
        phonemes = phonemes.replace("a^ʊ", "W")
        phonemes = phonemes.replace("d^z", "ʣ")
        phonemes = phonemes.replace("d^ʒ", "ʤ")
        phonemes = phonemes.replace("e^ɪ", "A")
        phonemes = phonemes.replace("o^ʊ", "O")
        phonemes = phonemes.replace("ə^ʊ", "Q")
        phonemes = phonemes.replace("s^s", "S")
        phonemes = phonemes.replace("t^s", "ʦ")
        phonemes = phonemes.replace("t^ʃ", "ʧ")
        phonemes = phonemes.replace("ɔ^ɪ", "Y")

    # Remove non-syllabic markers from diphthongs (U+032F)
    # The diphthongs work without this marker in Kokoro
    phonemes = phonemes.replace("\u032f", "")  # COMBINING INVERTED BREVE BELOW

    # Remove syllabic consonant marker (U+0329)
    # Syllabic consonants like n̩, l̩, m̩ work without this marker in Kokoro
    phonemes = phonemes.replace("\u0329", "")  # COMBINING VERTICAL LINE BELOW

    # Replace IPA characters not in Kokoro vocab with closest equivalents
    phonemes = phonemes.replace("ʏ", "y")  # LATIN SMALL CAPITAL Y -> lowercase y

    return phonemes


class GermanG2P(G2PBase):
    """German G2P converter using dictionary lookup with fallback options.

    This class provides grapheme-to-phoneme conversion for German text
    using a large dictionary (738k+ entries) with fallback to espeak-ng
    or goruut for out-of-vocabulary words and phonological rules.

    Example:
        >>> g2p = GermanG2P()
        >>> tokens = g2p("Guten Tag")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    def __init__(
        self,
        language: str = "de-de",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_lexicon: bool = True,
        strip_stress: bool = True,
        load_silver: bool = True,
        load_gold: bool = True,
        version: str = "1.0",
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the German G2P converter.

        Args:
            language: Language code (default: 'de-de').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            use_lexicon: Whether to use dictionary lookup (default: True).
            strip_stress: Whether to remove stress markers from lexicon output.
            load_silver: If True, load silver tier dictionary if available.
                Currently German only has gold dictionary, so this parameter
                is reserved for future use and consistency with English.
                Defaults to True for consistency.
            load_gold: If True, load gold tier dictionary.
                Defaults to True for maximum quality and coverage.
                Set to False when ultra-fast initialization is needed.
            expand_abbreviations: Whether to expand abbreviations (Prof. → Professor).
            enable_context_detection: Context-aware abbreviation expansion.

        Raises:
            ValueError: If both use_espeak_fallback and use_goruut_fallback are True.
        """
        # Validate mutual exclusion
        if use_espeak_fallback and use_goruut_fallback:
            raise ValueError(
                "Cannot use both espeak and goruut fallback simultaneously. "
                "Please set only one of use_espeak_fallback or "
                "use_goruut_fallback to True."
            )

        super().__init__(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
        )
        self.version = version
        self._lexicon: GermanLexicon | None = None
        self._fallback: Any = None
        self._strip_stress = strip_stress

        # Initialize normalizer
        from kokorog2p.de.normalizer import GermanNormalizer

        self._normalizer = GermanNormalizer(
            track_changes=False,
            expand_abbreviations=expand_abbreviations,
            enable_context_detection=enable_context_detection,
        )

        if use_lexicon:
            try:
                from kokorog2p.de.lexicon import GermanLexicon

                self._lexicon = GermanLexicon(
                    strip_stress=strip_stress,
                    load_silver=load_silver,
                    load_gold=load_gold,
                )
            except ImportError:
                pass

        # Initialize fallback (lazy)
        if use_goruut_fallback:
            try:
                from kokorog2p.de.fallback import GermanGoruutFallback

                self._fallback = GermanGoruutFallback()
            except ImportError:
                pass
        elif use_espeak_fallback:
            try:
                from kokorog2p.de.fallback import GermanEspeakFallback

                self._fallback = GermanEspeakFallback()
            except ImportError:
                pass

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        if not text or not text.strip():
            return []

        # Normalize text (expand abbreviations, normalize quotes, etc.)
        text = self._normalizer(text)

        tokens: list[GToken] = []

        # Tokenize by whitespace and punctuation
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
            else:
                # Try lexicon first
                phonemes = None
                if self._lexicon:
                    phonemes = self._lexicon.lookup(word)
                    if phonemes:
                        token.phonemes = normalize_to_kokoro(phonemes)
                        token.set("rating", 5)  # Dictionary lookup = highest rating

                # Fallback to espeak or goruut
                if not phonemes and self._fallback:
                    phonemes, rating = self._fallback(word)
                    if phonemes:
                        token.phonemes = phonemes
                        token.set("rating", 3)  # Fallback

                # Fallback to rules
                if not phonemes:
                    phonemes = self._word_to_phonemes(word)
                    if phonemes:
                        token.phonemes = normalize_to_kokoro(phonemes)
                        token.set("rating", 2)  # Rule-based

                if not phonemes:
                    token.phonemes = "?"
                    token.set("rating", 0)

            tokens.append(token)

        ensure_gtoken_positions(tokens, text)
        return tokens

    def _word_to_phonemes(self, word: str) -> str:
        """Convert a single word to phonemes using German rules.

        Args:
            word: Word to convert.

        Returns:
            Phoneme string in IPA.
        """
        text = word.lower()
        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            matched = False

            # Try to match multi-character sequences first (longest match)
            for length in (4, 3, 2):
                if i + length <= n:
                    chunk = text[i : i + length]

                    # Special handling for 'ch'
                    if chunk == "ch" and length == 2:
                        # ich-Laut vs ach-Laut
                        if i == 0:
                            # Word-initial ch (loan words) -> [ç] or [k]
                            result.append("ç")
                        elif i > 0 and _is_front_vowel_context(text[i - 1]):
                            # After front vowels and l, n, r -> ich-Laut [ç]
                            result.append("ç")
                        else:
                            # After back vowels a, o, u, au -> ach-Laut [x]
                            result.append("x")
                        i += 2
                        matched = True
                        break

                    # Special handling for word-initial sp, st
                    if chunk in ("sp", "st") and length == 2:
                        if i == 0:
                            # Word-initial sp/st -> [ʃp]/[ʃt]
                            result.append("ʃ")
                            result.append(chunk[1])
                            i += 2
                            matched = True
                            break
                        # Not word-initial, handle normally
                        continue

                    # Special handling for 'ig' at word end
                    if chunk == "ig" and length == 2 and i + 2 == n:
                        result.append("ɪ")
                        result.append("ç")  # -ig -> [ɪç] at word end
                        i += 2
                        matched = True
                        break

                    # Check if chunk is in IPA mappings
                    if chunk in IPA:
                        result.append(IPA[chunk])
                        i += length
                        matched = True
                        break

            if matched:
                continue

            # Single character
            char = text[i]

            # Special handling for vowels - check for length
            if char in "aeiouäöü":
                phoneme = self._get_vowel_phoneme(text, i)
                result.append(phoneme)
                i += 1
                continue

            # Special handling for 's'
            if char == "s":
                # Word-final or before unvoiced consonant -> [s]
                if i == n - 1:
                    result.append("s")
                elif i + 1 < n and text[i + 1] in "ptk":
                    result.append("s")
                else:
                    # Before vowel -> [z]
                    result.append("z")
                i += 1
                continue

            # Special handling for 'v'
            if char == "v":
                # In some loan words, 'v' is [v], but default is [f]
                result.append("f")
                i += 1
                continue

            # Special handling for 'r'
            if char == "r":
                # Vocalized r at end of syllable/word often becomes [ɐ]
                # For simplicity, use [ʁ] everywhere
                result.append("ʁ")
                i += 1
                continue

            # Check IPA mapping
            if char in IPA:
                result.append(IPA[char])
            elif char.isalpha():
                # Unknown letter, keep as-is or use placeholder
                result.append(char)
            # Skip non-alphabetic characters

            i += 1

        # Apply final devoicing
        result = self._apply_final_devoicing(result)

        return "".join(result)

    def _get_vowel_phoneme(self, text: str, pos: int) -> str:
        """Determine the correct vowel phoneme based on context.

        German vowel length is determined by syllable structure:
        - Long in open syllables (single consonant + vowel follows)
        - Long before single consonant at word end in many cases
        - Short before consonant clusters
        - Schwa (ə) in unstressed endings like -e, -en, -el, -er

        Args:
            text: The full word text.
            pos: Position of the vowel in the word.

        Returns:
            IPA phoneme for the vowel.
        """
        char = text[pos]

        # Short vowel mappings
        short_vowels: dict[str, str] = {
            "a": "a",
            "e": "ɛ",
            "i": "ɪ",
            "o": "ɔ",
            "u": "ʊ",
            "ä": "ɛ",
            "ö": "œ",
            "ü": "ʏ",
        }

        # Long vowel mappings
        long_vowels: dict[str, str] = {
            "a": "aː",
            "e": "eː",
            "i": "iː",
            "o": "oː",
            "u": "uː",
            "ä": "ɛː",
            "ö": "øː",
            "ü": "yː",
        }

        # Check what follows
        remaining = text[pos + 1 :]

        # Special handling for 'e' - check for schwa
        if char == "e":
            # Word-final -e -> schwa
            if not remaining:
                return "ə"
            # -en, -el, -er at word end -> schwa
            if remaining in ("n", "l", "r", "m", "ns", "ln", "rn", "ls", "rs"):
                return "ə"
            # -end, -ent, -ens at word end (but not stressed like 'Trend')
            if remaining in ("nd", "nt", "ns") and pos > 0:
                return "ə"

        # Before 'h' + vowel or word end -> long
        if remaining.startswith("h") and (
            len(remaining) == 1 or remaining[1:2] in "aeiouäöü"
        ):
            return long_vowels.get(char, short_vowels.get(char, char))

        # Word-final vowel -> usually short except in some words
        if not remaining:
            return short_vowels.get(char, char)

        # Before single consonant at word end -> often long
        if len(remaining) == 1 and remaining[0] in "bcdfghjklmnpqrstvwxz":
            # Common pattern: V + single C at end = long vowel
            return long_vowels.get(char, short_vowels.get(char, char))

        # Before 'ch', 'ß' -> depends on word, often long
        if remaining.startswith(("ch", "ß")):
            return long_vowels.get(char, short_vowels.get(char, char))

        # Before single consonant + vowel (open syllable) -> long
        if (
            len(remaining) >= 2
            and remaining[0] in "bcdfghjklmnpqrstvwxz"
            and remaining[0] not in "ck"  # ck indicates short vowel
            and remaining[1] in "aeiouäöü"
        ):
            # But 'sch' is one sound, not cluster
            if not remaining.startswith("sch"):
                return long_vowels.get(char, short_vowels.get(char, char))

        # Before consonant cluster -> short
        if (
            len(remaining) >= 2
            and remaining[0] in "bcdfghjklmnpqrstvwxz"
            and remaining[1] in "bcdfghjklmnpqrstvwxz"
        ):
            return short_vowels.get(char, char)

        # Default to short
        return short_vowels.get(char, char)

    def _apply_final_devoicing(self, phonemes: list[str]) -> list[str]:
        """Apply German final obstruent devoicing (Auslautverhärtung).

        Only applies to the final consonant cluster of the word.

        Args:
            phonemes: List of phoneme strings.

        Returns:
            Modified list with final devoicing applied.
        """
        if not phonemes:
            return phonemes

        vowels = frozenset(
            [
                "a",
                "aː",
                "e",
                "eː",
                "ɛ",
                "ɛː",
                "i",
                "iː",
                "ɪ",
                "o",
                "oː",
                "ɔ",
                "u",
                "uː",
                "ʊ",
                "y",
                "yː",
                "ʏ",
                "ø",
                "øː",
                "œ",
                "ə",
                "ɐ",
                "aɪ",
                "aʊ",
                "ɔʏ",
            ]
        )

        # Find the last consonant cluster (after the last vowel)
        last_vowel_idx = -1
        for i in range(len(phonemes) - 1, -1, -1):
            if phonemes[i] in vowels:
                last_vowel_idx = i
                break

        # Devoice all voiced obstruents after the last vowel
        for i in range(last_vowel_idx + 1, len(phonemes)):
            phone = phonemes[i]
            if phone in VOICED_TO_UNVOICED:
                phonemes[i] = VOICED_TO_UNVOICED[phone]

        return phonemes

    @staticmethod
    def _get_punct_phonemes(text: str) -> str:
        """Get phonemes for punctuation tokens.

        Only includes punctuation that exists in the Kokoro vocabulary.
        """
        # Punctuation marks that exist in Kokoro vocab
        # See kokorog2p/data/kokoro_config.json
        puncts = frozenset(';:,.!?"()')
        return "".join(c for c in text if c in puncts)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the dictionary.

        Args:
            word: The word to look up.
            tag: Optional POS tag (not used for German).

        Returns:
            Phoneme string if found, None otherwise.
        """
        if self._lexicon:
            return self._lexicon.lookup(word)
        return None

    def phonemize(self, text: str) -> str:
        """Convert text to a phoneme string.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string.
        """
        tokens = self(text)
        return " ".join(t.phonemes or "" for t in tokens if t.phonemes)

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
