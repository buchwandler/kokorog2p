"""French lexicon for G2P lookup.

Based on misaki French implementation, adapted for kokorog2p.
"""

import unicodedata
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from kokorog2p.lexicons.runtime import SelectedLexicons, open_selected

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


def clear_lexicon_cache() -> None:
    """Compatibility hook retained for callers of the former JSON cache."""


def lexicon_cache_info():
    """Return compatibility cache statistics for the resource-backed lexicon."""
    from collections import namedtuple

    return namedtuple("LexiconCacheInfo", "hits misses maxsize currsize")(0, 0, 0, 0)


# =============================================================================
# Lexicon Class
# =============================================================================


class FrenchLexicon:
    """Dictionary-based G2P lookup for French with gold dictionary."""

    def __init__(
        self,
        load_silver: bool = True,
        load_gold: bool = True,
        lexicons: Sequence[str] | None = None,
    ) -> None:
        """Initialize the French lexicon."""
        del load_silver
        names = (
            ("gold",)
            if lexicons is None and load_gold
            else ()
            if lexicons is None
            else tuple(lexicons)
        )
        self._selected: SelectedLexicons = open_selected("fr-fr", names)
        self.golds: LexiconMapping = self._selected.layer("gold") or EMPTY_LEXICON
        self.silvers: LexiconMapping = self._selected.layer("silver") or EMPTY_LEXICON
        self.load_silver = False
        self.load_gold = "gold" in names
        self.lexicons = names
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
            word in self._selected
            or word_lower in self._selected
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
        hit = self._selected.get_hit(word)
        if hit is None:
            hit = self._selected.get_hit(word_lower)
        if hit is None:
            return (None, None)
        ps = hit.value
        rating = hit.rating
        if isinstance(ps, Mapping):
            if tag and tag in ps:
                ps = ps[tag]
            elif "DEFAULT" in ps:
                ps = ps["DEFAULT"]
            else:
                ps = next(iter(ps.values()))
        elif isinstance(ps, tuple):
            ps = ps[0] if ps else None
        return (ps if isinstance(ps, str) else None, rating)

    def close(self) -> None:
        self._selected.close()

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
