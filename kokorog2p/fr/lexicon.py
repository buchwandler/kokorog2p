"""French lexicon for G2P lookup.

Based on misaki French implementation, adapted for kokorog2p.
"""

import importlib.resources
import json
import unicodedata
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from types import MappingProxyType
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

# =============================================================================
# Helper Classes
# =============================================================================


@dataclass
class TokenContext:
    """Context information for token processing."""

    future_vowel: bool | None = None
    liaison: bool = False


LexiconValue = str | dict[str, str | None]
LexiconMapping = Mapping[str, LexiconValue]
EMPTY_LEXICON: Final[LexiconMapping] = MappingProxyType({})


@lru_cache(maxsize=1)
def _load_dictionary() -> LexiconMapping:
    """Load and expand the immutable French gold dictionary once."""
    files = importlib.resources.files(data)
    with (files / "fr_gold.json").open("r", encoding="utf-8") as stream:
        loaded: dict[str, LexiconValue] = json.load(stream)

    for word, pronunciation in tuple(loaded.items()):
        if len(word) < 2:
            continue
        if word == word.lower():
            loaded.setdefault(word.capitalize(), pronunciation)
        elif word == word.lower().capitalize():
            loaded.setdefault(word.lower(), pronunciation)

    return MappingProxyType(loaded)


def clear_lexicon_cache() -> None:
    """Release the cached French dictionary mapping."""
    _load_dictionary.cache_clear()


def lexicon_cache_info():
    """Return cache statistics for the French dictionary resource."""
    return _load_dictionary.cache_info()


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
        self.golds: LexiconMapping = EMPTY_LEXICON
        self.silvers: LexiconMapping = EMPTY_LEXICON

        # Load gold dictionary if requested
        if load_gold:
            self.golds = _load_dictionary()

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
        if isinstance(ps, dict) and isinstance(ps, dict):
            if tag and tag in ps:
                return (ps[tag], 4)
            return (ps.get("DEFAULT", next(iter(ps.values()))), 4)
        return (ps, 4)

    def expand_abbreviation(self, text: str) -> str:
        """Compatibility shim for the former local abbreviation registry.

        New code should use ``abbr2words`` or ``FrenchNormalizer``. Keeping
        this method avoids an abrupt API break without retaining a duplicate
        registry in the French G2P path.
        """
        warnings.warn(
            "FrenchLexicon.expand_abbreviation is deprecated; use abbr2words.",
            DeprecationWarning,
            stacklevel=2,
        )
        from abbr2words import get_shared_expander

        return get_shared_expander("fr", context=True).expand(text)

    def expand_ordinals(self, text: str) -> str:
        """Deprecated compatibility shim for upstream ordinal preparation."""
        warnings.warn(
            "FrenchLexicon.expand_ordinals is deprecated; use spokenform.",
            DeprecationWarning,
            stacklevel=2,
        )
        from kokorog2p.fr.numbers import expand_ordinal

        return expand_ordinal(text)

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
