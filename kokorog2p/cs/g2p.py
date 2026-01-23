"""Czech G2P (Grapheme-to-Phoneme) converter.

Grapheme to Phoneme for Czech language.
Originally developed by Richard Mazur:
https://github.com/essare-rimaz/grapheme_to_phoneme_CZ/blob/main/server.r

Later converted to Python by Miroslav Suchy <msuchy@redhat.com> with
assistance of AI. And with permission of Richard released under Apache-2.0
license.

Adapted for kokorog2p architecture.

Czech Phonology reference:
https://cs.wikipedia.org/wiki/Fonologie_%C4%8De%C5%A1tiny
"""

import re
from typing import Any, Final

from kokorog2p.base import G2PBase
from kokorog2p.cs.normalizer import CzechNormalizer
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

# =============================================================================
# Czech Phoneme Mappings
# =============================================================================

# IPA mappings for Czech graphemes
IPA: Final[dict[str, str]] = {
    "a": "a",
    "á": "aː",
    "b": "b",
    "c": "t͡s",
    "č": "t͡ʃ",
    "d": "d",
    "ď": "ɟ",
    "e": "ɛ",
    "é": "ɛː",
    "ě": "ě",
    "f": "f",
    "g": "ɡ",
    "h": "ɦ",
    "ch": "x",
    "i": "ɪ",
    "í": "iː",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "ň": "ň",
    "o": "o",
    "ó": "oː",
    "p": "p",
    "q": "k",
    "r": "r",
    "s": "s",
    "š": "ʃ",
    "t": "t",
    "ť": "c",
    "u": "u",
    "ú": "uː",
    "ů": "uː",
    "v": "v",
    "w": "w",
    "x": "ks",
    "y": "ɪ",
    "ý": "iː",
    "z": "z",
    "ž": "ʒ",
    "di": "ɟɪ",
    "dí": "ɟiː",
    "dě": "ɟɛ",
    "ti": "cɪ",
    "tí": "ciː",
    "tě": "cɛ",
    "ni": "ɲɪ",
    "ní": "ɲiː",
    "ně": "ɲɛ",
    "mě": "mɲɛ",
    "bě": "bjɛ",
    "pě": "pjɛ",
    "vě": "vjɛ",
    "ts": "t͡s",
    "dz": "d͡z",
    "ie": "ɪjɛ",
    "ia": "ɪja",
    "io": "ɪjo",
    "ř": "r̝",
}

# Temporary representation for processing
TEMP: Final[dict[str, str]] = {
    "a": "a",
    "á": "á",
    "b": "b",
    "c": "c",
    "č": "č",
    "d": "d",
    "ď": "ď",
    "e": "e",
    "é": "é",
    "ě": "ě",
    "f": "f",
    "g": "g",
    "h": "h",
    "ch": "ch",
    "i": "i",
    "í": "í",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "ň": "ň",
    "o": "o",
    "ó": "ó",
    "p": "p",
    "q": "q",
    "r": "r",
    "ř": "ř",
    "s": "s",
    "š": "š",
    "t": "t",
    "ť": "ť",
    "u": "u",
    "ú": "ú",
    "ů": "ů",
    "v": "v",
    "w": "w",
    "x": "x",
    "y": "y",
    "ý": "ý",
    "z": "z",
    "ž": "ž",
    "di": "di",
    "dí": "dí",
    "dě": "dě",
    "ti": "ti",
    "tí": "tí",
    "tě": "tě",
    "ni": "ni",
    "ní": "ní",
    "ně": "ně",
    "mě": "mě",
    "bě": "bě",
    "pě": "pě",
    "vě": "vě",
    "dz": "dz",
    "ts": "ts",
    "ie": "ie",
    "ia": "ia",
    "io": "io",
    " ": " ",
}

# Consonant voicing pairs
PAIRED_CONSONANTS: Final[dict[str, str]] = {
    "b": "p",
    "d": "t",
    "ď": "ť",
    "g": "k",
    "v": "f",
    "z": "s",
    "ž": "š",
    "ch": "h",
    "dz": "c",
    "dž": "č",
    "p": "b",
    "t": "d",
    "ť": "ď",
    "k": "g",
    "f": "v",
    "s": "z",
    "š": "ž",
    "h": "ch",
    "c": "dz",
    "č": "dž",
}

PAIRED_UNVOICED: Final[dict[str, str]] = {
    "p": "p",
    "t": "t",
    "ť": "ť",
    "k": "k",
    "f": "f",
    "s": "s",
    "š": "š",
    "ch": "ch",
    "c": "c",
    "č": "č",
}

PAIRED_VOICED: Final[dict[str, str]] = {
    "b": "b",
    "d": "d",
    "ď": "ď",
    "g": "g",
    "v": "v",
    "z": "z",
    "ž": "ž",
    "dz": "dz",
    "dž": "dž",
}

# Consonant + vowel combinations
DTN: Final[dict[str, str]] = {"d": "d", "t": "t", "n": "n"}
DTN_VOCAL: Final[dict[str, str]] = {"í": "í", "i": "i", "ě": "ě"}

MBPV: Final[dict[str, str]] = {"m": "m", "b": "b", "p": "p", "v": "v"}
MBPV_VOCAL: Final[dict[str, str]] = {"ě": "ě"}

# Digraph detection
CH_FIRST: Final[dict[str, str]] = {"c": "c"}
CH_SECOND: Final[dict[str, str]] = {"h": "h"}

TS_FIRST: Final[dict[str, str]] = {"t": "t"}
TS_SECOND: Final[dict[str, str]] = {"s": "s"}

DZ_FIRST: Final[dict[str, str]] = {"d": "d"}
DZ_SECOND: Final[dict[str, str]] = {"z": "z"}

IEIAIO_FIRST: Final[dict[str, str]] = {"i": "i"}
IEIAIO_SECOND: Final[dict[str, str]] = {"e": "e", "a": "a", "o": "o"}


def _indices_where_in(v: list[str | None], keyset: dict[str, str]) -> list[int]:
    """Find indices where values are in keyset."""
    s = set(keyset.keys())
    return [i for i, x in enumerate(v) if x in s]


class CzechG2P(G2PBase):
    """Czech G2P converter using rule-based phoneme conversion with fallback options.

    This class provides grapheme-to-phoneme conversion for Czech text
    using phonological rules for voicing assimilation, palatalization,
    and other Czech-specific features, with optional fallback to espeak or goruut.

    Example:
        >>> g2p = CzechG2P()
        >>> tokens = g2p("Dobrý den")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    def __init__(
        self,
        language: str = "cs-cz",
        use_espeak_fallback: bool = False,
        use_goruut_fallback: bool = False,
        unk: str = "?",
        load_silver: bool = True,
        load_gold: bool = True,
        version: str = "1.0",
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        **kwargs: Any,
    ) -> None:
        """Initialize the Czech G2P converter.

        Args:
            language: Language code (default: 'cs-cz').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            unk: Character to use for unknown characters.
            load_silver: If True, load silver tier dictionary if available.
                Currently Czech uses rule-based G2P, so this parameter
                is reserved for future use and consistency.
                Defaults to True for consistency.
            load_gold: If True, load gold tier dictionary if available.
                Currently Czech uses rule-based G2P, so this parameter
                is reserved for future use and consistency.
                Defaults to True for consistency.
            expand_abbreviations: If True, expand common abbreviations
                (e.g., "Dr." → "Doktor"). Defaults to True.
            enable_context_detection: If True, use context-aware expansion
                for ambiguous abbreviations. Defaults to True.

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

        super().__init__(language=language, use_espeak_fallback=use_espeak_fallback)
        self.version = version
        self.unk = unk
        self.load_silver = load_silver
        self.load_gold = load_gold
        self.use_goruut_fallback = use_goruut_fallback
        self.expand_abbreviations = expand_abbreviations
        self.enable_context_detection = enable_context_detection
        self._fallback: Any = None

        # Initialize normalizer
        self._normalizer = CzechNormalizer(
            expand_abbreviations=expand_abbreviations,
            enable_context_detection=enable_context_detection,
        )

        # Initialize fallback (lazy)
        if use_goruut_fallback:
            try:
                from kokorog2p.cs.fallback import CzechGoruutFallback

                self._fallback = CzechGoruutFallback()
            except ImportError:
                pass
        elif use_espeak_fallback:
            try:
                from kokorog2p.cs.fallback import CzechEspeakFallback

                self._fallback = CzechEspeakFallback()
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

        # Apply normalization (abbreviations, temperature, quotes, etc.)
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
                # Convert word to phonemes using rules
                phonemes = self._word_to_phonemes(word)

                # Optionally use fallback if enabled
                # (Useful for loan words or foreign abbreviations)
                if not phonemes and self._fallback:
                    fallback_phonemes, rating = self._fallback(word)
                    if fallback_phonemes:
                        phonemes = fallback_phonemes
                        token.set("rating", 2)  # Fallback rating
                    else:
                        token.set("rating", 4)  # Rule-based
                else:
                    token.set("rating", 4)  # Rule-based

                token.phonemes = phonemes if phonemes else self.unk

            tokens.append(token)

        ensure_gtoken_positions(tokens, text)
        return tokens

    def _word_to_phonemes(self, word: str) -> str:  # noqa: C901
        """Convert a single word to phonemes using Czech rules.

        Args:
            word: Word to convert.

        Returns:
            Phoneme string in IPA.
        """
        text = word.lower()
        text_split = list(text)

        result: list[str | None] = []
        for ch in text_split:
            result.append(TEMP.get(ch))  # missing -> None

        # 1) i followed by e/a/o => ie/ia/io
        for x in _indices_where_in(result, IEIAIO_FIRST):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in IEIAIO_SECOND:
                    result[x] = (result[x] or "") + (result[y] or "")
                    result[y] = None

        # 2) d + z => dz
        for x in _indices_where_in(result, DZ_FIRST):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in DZ_SECOND:
                    result[x] = (result[x] or "") + (result[y] or "")
                    result[y] = None

        # 3) t + s => ts
        for x in _indices_where_in(result, TS_FIRST):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in TS_SECOND:
                    result[x] = (result[x] or "") + (result[y] or "")
                    result[y] = None

        # 4) voicing assimilation: unvoiced before voiced => swap with pair
        for x in _indices_where_in(result, PAIRED_UNVOICED):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in PAIRED_VOICED:
                    w = result[x]
                    if w is not None and w in PAIRED_CONSONANTS:
                        result[x] = PAIRED_CONSONANTS[w]

        # 5) voicing assimilation: voiced before unvoiced => swap with pair
        for x in _indices_where_in(result, PAIRED_VOICED):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in PAIRED_UNVOICED:
                    w = result[x]
                    if w is not None and w in PAIRED_CONSONANTS:
                        result[x] = PAIRED_CONSONANTS[w]

        # 6) c + h => ch
        for x in _indices_where_in(result, CH_FIRST):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in CH_SECOND:
                    result[x] = (result[x] or "") + (result[y] or "")
                    result[y] = None

        # 7) d/t/n + (i/í/ě) => di/dí/dě, ti/tí/tě, ni/ní/ně
        for x in _indices_where_in(result, DTN):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in DTN_VOCAL:
                    result[x] = (result[x] or "") + (result[y] or "")
                    result[y] = None

        # 8) m/b/p/v + ě => mě/bě/pě/vě
        for x in _indices_where_in(result, MBPV):
            y = x + 1
            if y < len(result):
                z = result[y]
                if z is not None and z in MBPV_VOCAL:
                    result[x] = (result[x] or "") + (result[y] or "")
                    result[y] = None

        # Final devoicing: if last symbol is voiced, replace with its pair
        if result:
            last_idx = len(result) - 1
            z = result[last_idx]
            if z is not None and z in PAIRED_VOICED and z in PAIRED_CONSONANTS:
                result[last_idx] = PAIRED_CONSONANTS[z]

        # Remove None values
        result_clean: list[str] = [x for x in result if x is not None]

        # Convert to IPA
        result_ipa: list[str] = []
        for token in result_clean:
            temp_val = TEMP.get(token, token)
            ipa_val = IPA.get(temp_val, temp_val)
            result_ipa.append(ipa_val)

        return "".join(result_ipa)

    @staticmethod
    def _get_punct_phonemes(text: str) -> str:
        """Get phonemes for punctuation tokens."""
        puncts = frozenset(";:,.!?-\"'()[]—…")
        return "".join("—" if c == "-" else c for c in text if c in puncts)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the dictionary.

        For Czech, this just converts the word to phonemes using rules.

        Args:
            word: The word to look up.
            tag: Optional POS tag (not used for Czech).

        Returns:
            Phoneme string.
        """
        return self._word_to_phonemes(word)

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
