"""French lexicon for G2P lookup.

Based on misaki French implementation, adapted for kokorog2p.
"""

import importlib.resources
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Final

from kokorog2p.fr import data

# =============================================================================
# Constants
# =============================================================================

# Valid character ordinals for lexicon lookup (includes French accented chars)
LEXICON_ORDS: Final[list[int]] = [
    39,  # '
    45,  # -
    *range(65, 91),  # A-Z
    *range(97, 123),  # a-z
    192,  # À
    194,  # Â
    196,  # Ä
    199,  # Ç
    200,  # È
    201,  # É
    202,  # Ê
    203,  # Ë
    206,  # Î
    207,  # Ï
    212,  # Ô
    217,  # Ù
    219,  # Û
    220,  # Ü
    224,  # à
    226,  # â
    228,  # ä
    231,  # ç
    232,  # è
    233,  # é
    234,  # ê
    235,  # ë
    238,  # î
    239,  # ï
    244,  # ô
    249,  # ù
    251,  # û
    252,  # ü
    339,  # œ
    338,  # Œ
    230,  # æ
    198,  # Æ
]

# Consonants (French)
CONSONANTS: Final[frozenset[str]] = frozenset("bdfhjklmnpstvwzðŋɲɡʁʃʒ")

# Vowels (French including nasal vowels)
VOWELS: Final[frozenset[str]] = frozenset("aeiouyøœəɛɔɑɑ̃ɛ̃ɔ̃œ̃")

# Semi-vowels
SEMI_VOWELS: Final[frozenset[str]] = frozenset("jwɥ")

# Symbol mappings
SYMBOLS: Final[dict[str, str]] = {
    "%": "pour cent",
    "&": "et",
    "+": "plus",
    "@": "arobase",
}

# Currency symbols
CURRENCIES: Final[dict[str, tuple[str, str]]] = {
    "€": ("euro", "centime"),
    "$": ("dollar", "cent"),
    "£": ("livre", "pence"),
}

# Common French abbreviations
ABBREVIATIONS: Final[dict[str, str]] = {
    # Titles
    "M.": "monsieur",
    "Mme": "madame",
    "Mlle": "mademoiselle",
    "Dr": "docteur",
    "Pr": "professeur",
    "Me": "maître",
    "Mgr": "monseigneur",
    "St": "saint",
    "Ste": "sainte",
    # Common abbreviations
    "etc.": "et cetera",
    "cf.": "confer",
    "ex.": "exemple",
    "n°": "numéro",
    "N°": "numéro",
    "p.": "page",
    "pp.": "pages",
    "vol.": "volume",
    "chap.": "chapitre",
    "éd.": "édition",
    "env.": "environ",
    "min.": "minute",
    "sec.": "seconde",
    "h": "heure",
    "km": "kilomètre",
    "m": "mètre",
    "cm": "centimètre",
    "mm": "millimètre",
    "kg": "kilogramme",
    "g": "gramme",
    "mg": "milligramme",
    "l": "litre",
    "ml": "millilitre",
}

# Ordinal suffixes
ORDINALS: Final[dict[str, str]] = {
    "1er": "premier",
    "1ère": "première",
    "1re": "première",
    "2e": "deuxième",
    "2ème": "deuxième",
    "2nd": "second",
    "2nde": "seconde",
    "3e": "troisième",
    "3ème": "troisième",
}


# =============================================================================
# Helper Classes
# =============================================================================


@dataclass
class TokenContext:
    """Context information for token processing."""

    future_vowel: bool | None = None
    liaison: bool = False


# =============================================================================
# Lexicon Class
# =============================================================================


class FrenchLexicon:
    """Dictionary-based G2P lookup for French with gold dictionary."""

    def __init__(self, load_silver: bool = True, load_gold: bool = True) -> None:
        """Initialize the French lexicon.

        Args:
            load_silver: If True, load silver tier dictionary if available.
                Currently French only has gold dictionary, so this parameter
                is reserved for future use and consistency with English.
                Defaults to True for consistency.
            load_gold: If True, load gold tier dictionary.
                Defaults to True for maximum quality and coverage.
                Set to False when ultra-fast initialization is needed.
        """
        self.load_silver = load_silver
        self.load_gold = load_gold
        self.golds: dict[str, str | dict[str, str | None]] = {}
        self.silvers: dict[str, str] = {}

        # Load gold dictionary if requested
        if load_gold:
            files = importlib.resources.files(data)
            with (files / "fr_gold.json").open("r", encoding="utf-8") as r:
                self.golds = self._grow_dictionary(json.load(r))

        # Silver dictionary not yet available for French
        # When available, load it conditionally:
        # if load_silver:
        #     with importlib.resources.open_text(data, "fr_silver.json") as r:
        #         self.silvers = self._grow_dictionary(json.load(r))

        # Initialize built-in pronunciation fixes (highest priority)
        self._init_builtin_fixes()

    def _init_builtin_fixes(self) -> None:
        """Initialize built-in pronunciation corrections.

        These override dictionary pronunciations for common errors.
        """
        self.builtin: dict[str, str] = {
            # Verbs with -ait/-ais (imparfait) - often mispronounced
            "était": "etɛ",
            "étais": "etɛ",
            "étaient": "etɛ",
            "avait": "avɛ",
            "avais": "avɛ",
            "avaient": "avɛ",
            "fait": "fɛ",
            "fais": "fɛ",
            "faite": "fɛt",
            "faites": "fɛt",
            "savait": "savɛ",
            "savais": "savɛ",
            "disait": "dizɛ",
            "faisait": "fəzɛ",
            "allait": "alɛ",
            "venait": "vənɛ",
            "devait": "dəvɛ",
            "pouvait": "puvɛ",
            "voulait": "vulɛ",
            # Common words
            "monsieur": "məsjø",
            "messieurs": "mesjø",
            "madame": "madam",
            "mademoiselle": "madmwazɛl",
            "aujourd'hui": "oʒuʁdɥi",
            # Silent letters and liaisons
            "les": "le",
            "des": "de",
            "est": "ɛ",
            "et": "e",
        }

    @staticmethod
    def _grow_dictionary(d: dict[str, Any]) -> dict[str, Any]:
        """Expand dictionary with capitalization variants.

        Args:
            d: Original dictionary.

        Returns:
            Expanded dictionary with capitalized variants.
        """
        e: dict[str, Any] = {}
        for k, v in d.items():
            if len(k) < 2:
                continue
            if k == k.lower():
                cap = k.capitalize()
                if k != cap:
                    e[cap] = v
            elif k == k.lower().capitalize():
                e[k.lower()] = v
        return {**e, **d}

    def is_known(self, word: str, tag: str | None = None) -> bool:
        """Check if a word is in the lexicon."""
        word_lower = word.lower()
        return (
            word in self.golds
            or word_lower in self.golds
            or word_lower in self.builtin
            or word in SYMBOLS
        )

    def lookup(
        self,
        word: str,
        tag: str | None = None,
        ctx: TokenContext | None = None,
    ) -> tuple[str | None, int | None]:
        """Look up a word in the lexicon.

        Args:
            word: Word to look up.
            tag: POS tag (optional).
            ctx: Token context (optional).

        Returns:
            Tuple of (phonemes, rating) or (None, None) if not found.
        """
        word_lower = word.lower()

        # Check built-in fixes first (highest priority after gold)
        if word_lower in self.builtin:
            return (self.builtin[word_lower], 4)

        # Check gold dictionary
        ps = self.golds.get(word) or self.golds.get(word_lower)

        if ps is None:
            return (None, None)

        # Handle heteronyms (dict entries)
        if isinstance(ps, dict):
            if isinstance(ps, dict):
                if tag and tag in ps:
                    return (ps[tag], 4)
                return (ps.get("DEFAULT", list(ps.values())[0]), 4)
        return (ps, 4)

    def expand_abbreviation(self, text: str) -> str:
        """Expand common French abbreviations."""
        for abbr, expansion in ABBREVIATIONS.items():
            pattern = re.escape(abbr)
            if abbr.endswith("."):
                text = re.sub(
                    rf"\b{pattern}(?=\s|$|[,;:!?])",
                    expansion,
                    text,
                    flags=re.IGNORECASE,
                )
            else:
                text = re.sub(rf"\b{pattern}\b", expansion, text, flags=re.IGNORECASE)
        return text

    def expand_ordinals(self, text: str) -> str:
        """Expand ordinal numbers."""
        for ordinal, expansion in ORDINALS.items():
            text = re.sub(
                rf"\b{re.escape(ordinal)}\b", expansion, text, flags=re.IGNORECASE
            )
        return text

    def get_special_case(
        self,
        word: str,
        tag: str | None,
        ctx: TokenContext | None,
    ) -> tuple[str | None, int | None]:
        """Handle special case words with context-dependent pronunciations."""
        if word in SYMBOLS:
            return self.lookup(SYMBOLS[word], None, ctx)
        return (None, None)

    @staticmethod
    def normalize_word(word: str) -> str:
        """Normalize a word for lookup."""
        # Replace curly quotes
        word = word.replace(chr(8216), "'").replace(chr(8217), "'")
        # Normalize unicode
        word = unicodedata.normalize("NFC", word)
        return word

    def __call__(
        self,
        word: str,
        tag: str | None = None,
        ctx: TokenContext | None = None,
    ) -> tuple[str | None, int | None]:
        """Look up phonemes for a word.

        Args:
            word: Word to look up.
            tag: POS tag.
            ctx: Token context.

        Returns:
            Tuple of (phonemes, rating) or (None, None) if not found.
        """
        # Normalize the word
        word = self.normalize_word(word)

        # Check special cases first
        ps, rating = self.get_special_case(word, tag, ctx)
        if ps is not None:
            return (ps, rating)

        # Standard lookup
        return self.lookup(word, tag, ctx)
