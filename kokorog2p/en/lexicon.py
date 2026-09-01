"""Lexicon-based G2P lookup for English.

Based on misaki by hexgrad, adapted for kokorog2p.
"""

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

from kokorog2p.lexicons.runtime import LexiconHit, SelectedLexicons, open_selected

# =============================================================================
# Constants
# =============================================================================

# Valid character ordinals for lexicon lookup
LEXICON_ORDS: Final[list[int]] = [39, 45, *range(65, 91), *range(97, 123)]

# Consonants
CONSONANTS: Final[frozenset[str]] = frozenset("bdfhjklmnpstvwzðŋɡɹɾʃʒʤʧθ")

# Vowels
VOWELS: Final[frozenset[str]] = frozenset("AIOQWYaiuæɑɒɔəɛɜɪʊʌᵻ")
DIPHTHONGS: Final[frozenset[str]] = frozenset("AIOQWYʤʧ")

# US taus - vowels that can trigger flapping
US_TAUS: Final[frozenset[str]] = frozenset("AIOWYiuæɑəɛɪɹʊʌ")

# Stress markers
PRIMARY_STRESS: Final[str] = "ˈ"
SECONDARY_STRESS: Final[str] = "ˌ"
STRESSES: Final[str] = SECONDARY_STRESS + PRIMARY_STRESS

# Symbol mappings
ADD_SYMBOLS: Final[dict[str, str]] = {".": "dot", "/": "slash"}
SYMBOLS: Final[dict[str, str]] = {"%": "percent", "&": "and", "+": "plus", "@": "at"}

# Currency symbols
CURRENCIES: Final[dict[str, tuple[str, str]]] = {
    "$": ("dollar", "cent"),
    "£": ("pound", "pence"),
    "€": ("euro", "cent"),
}

# Ordinal suffixes
ORDINALS: Final[frozenset[str]] = frozenset(["st", "nd", "rd", "th"])

# Greek letter mappings (uppercase and lowercase)
GREEK_LETTERS: Final[dict[str, str]] = {
    "Α": "alpha",
    "α": "alpha",
    "Β": "beta",
    "β": "beta",
    "Γ": "gamma",
    "γ": "gamma",
    "Δ": "delta",
    "δ": "delta",
    "Ε": "epsilon",
    "ε": "epsilon",
    "Ζ": "zeta",
    "ζ": "zeta",
    "Η": "eta",
    "η": "eta",
    "Θ": "theta",
    "θ": "theta",
    "Ι": "iota",
    "ι": "iota",
    "Κ": "kappa",
    "κ": "kappa",
    "Λ": "lambda",
    "λ": "lambda",
    "Μ": "mu",
    "μ": "mu",
    "Ν": "nu",
    "ν": "nu",
    "Ξ": "xi",
    "ξ": "xi",
    "Ο": "omicron",
    "ο": "omicron",
    "Π": "pi",
    "π": "pi",
    "Ρ": "rho",
    "ρ": "rho",
    "Σ": "sigma",
    "σ": "sigma",
    "ς": "sigma",
    "Τ": "tau",
    "τ": "tau",
    "Υ": "upsilon",
    "υ": "upsilon",
    "Φ": "phi",
    "φ": "phi",
    "Χ": "chi",
    "χ": "chi",
    "Ψ": "psi",
    "ψ": "psi",
    "Ω": "omega",
    "ω": "omega",
}


# =============================================================================
# Helper Classes
# =============================================================================


@dataclass
class TokenContext:
    """Context information for token processing."""

    future_vowel: bool | None = None
    future_to: bool = False


LexiconValue = str | Mapping[str, str | None] | tuple[str, ...]
LexiconMapping = Mapping[str, LexiconValue]
EMPTY_LEXICON: Final[LexiconMapping] = MappingProxyType({})


def clear_lexicon_cache() -> None:
    """Compatibility wrapper for the shared G2Lex resource cache."""
    from kokorog2p.lexicons.runtime import clear_resource_cache

    clear_resource_cache()


def lexicon_cache_info():
    """Return diagnostics for the shared resource-backed lexicon cache."""
    from kokorog2p.lexicons.runtime import resource_cache_info

    return resource_cache_info()


# =============================================================================
# Stress Functions
# =============================================================================


def apply_stress(ps: str | None, stress: float | None) -> str | None:
    """Apply English stress modification using the shared state machine."""
    from kokorog2p.stress import apply_stress as _apply_stress

    return _apply_stress(ps, stress, vowels=VOWELS)


def stress_weight(ps: str | None) -> int:
    """Calculate the "weight" of a phoneme string for stress assignment."""
    if not ps:
        return 0
    return sum(2 if c in DIPHTHONGS else 1 for c in ps)


def is_digit(text: str) -> bool:
    """Check if text consists only of digits."""
    return bool(re.match(r"^[0-9]+$", text))


# =============================================================================
# Lexicon Class
# =============================================================================


class Lexicon:
    """Dictionary-based G2P lookup with gold and silver tier dictionaries."""

    def __init__(
        self,
        british: bool = False,
        skip_is_known: bool = False,
        load_silver: bool = True,
        load_gold: bool = True,
        lexicons: Sequence[str] | None = None,
    ) -> None:
        """Initialize the lexicon.

        Args:
            british: Whether to use British English dictionaries.
            skip_is_known: If True, skip is_known checks (useful for benchmarking).
            load_silver: If True, load silver tier dictionary (~100k extra entries).
                Defaults to True for backward compatibility and maximum coverage.
                Set to False to save memory (~22-31 MB) and initialization time.
            load_gold: If True, load gold tier dictionary (~170k common words).
                Defaults to True for maximum quality and coverage.
                Set to False when only silver tier or no dictionaries needed.
        """
        self.british = british
        self.skip_is_known = skip_is_known
        self.load_silver = load_silver
        self.load_gold = load_gold
        self.cap_stresses = (0.5, 2)
        language = "en-gb" if british else "en-us"
        names = (
            ("gold", "silver")
            if lexicons is None and load_gold and load_silver
            else ("gold",)
            if lexicons is None and load_gold
            else ("silver",)
            if lexicons is None and load_silver
            else ()
            if lexicons is None
            else tuple(lexicons)
        )
        self.lexicons = names
        self._selected: SelectedLexicons = open_selected(language, names)
        self.golds: LexiconMapping = self._selected.layer("gold") or EMPTY_LEXICON
        self.silvers: LexiconMapping = self._selected.layer("silver") or EMPTY_LEXICON

    def _selected_hit(self, word: str) -> LexiconHit | None:
        """Return the hit selected by the configured ordered stack."""
        hit = self._selected.get_hit(word)
        if hit is not None:
            return hit

        # Keep the public tier mappings usable for deterministic callers that
        # replace them with an in-memory fixture after construction.
        for name, mapping, rating in (
            ("gold", self.golds, 4),
            ("silver", self.silvers, 3),
        ):
            try:
                value = mapping[word]
            except KeyError:
                continue
            return LexiconHit(
                value=value,
                name=name,
                rating=rating,
                kind="pronunciation",
                phoneme_encoding="ipa",
                lexicon_id=f"en-us:{name}:compatibility",
                metadata={},
            )
        return None

    def _contains_selected(self, word: str) -> bool:
        """Check membership without assuming tier names."""
        return self._selected_hit(word) is not None

    def _get_hit(self, word: str) -> LexiconHit | None:
        return self._selected_hit(word)

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

    @staticmethod
    def get_parent_tag(tag: str | None) -> str | None:
        """Get parent POS tag category."""
        if tag is None:
            return tag
        elif tag.startswith("VB"):
            return "VERB"
        elif tag.startswith("NN"):
            return "NOUN"
        elif tag.startswith(("ADV", "RB")):
            return "ADV"
        elif tag.startswith(("ADJ", "JJ")):
            return "ADJ"
        return tag

    def is_known(self, word: str, tag: str | None = None) -> bool:
        """Check if a word is in the lexicon."""
        if self._get_hit(word) is not None or word in SYMBOLS:
            return True
        elif not word.isalpha() or not all(ord(c) in LEXICON_ORDS for c in word):
            return False
        elif len(word) == 1 or (
            word == word.upper() and self._contains_selected(word.lower())
        ):
            return True
        return word[1:] == word[1:].upper()

    def get_NNP(self, word: str) -> tuple[str | None, int | None]:
        """Get phonemes for a proper noun by spelling."""
        ps = [
            hit.value if (hit := self._get_hit(c.upper())) is not None else None
            for c in word
            if c.isalpha()
        ]
        if None in ps:
            return None, None
        ps_str = apply_stress("".join(str(p) for p in ps if isinstance(p, str)), 0)
        if ps_str is None:
            return None, None
        parts = ps_str.rsplit(SECONDARY_STRESS, 1)
        return PRIMARY_STRESS.join(parts), 3

    def lookup(
        self,
        word: str,
        tag: str | None = None,
        stress: float | None = None,
        ctx: TokenContext | None = None,
    ) -> tuple[str | None, int | None]:
        """Look up a word in the lexicon.

        Args:
            word: Word to look up.
            tag: POS tag.
            stress: Stress level.
            ctx: Token context.

        Returns:
            Tuple of (phonemes, rating) or (None, None) if not found.
        """
        is_NNP = None
        if word == word.upper() and word not in self._selected:
            word = word.lower()
            is_NNP = tag == "NNP"

        hit = self._get_hit(word)
        ps = hit.value if hit is not None else None
        rating = hit.rating if hit is not None and hit.rating is not None else 4
        if isinstance(ps, Mapping):
            if ctx and ctx.future_vowel is None and "None" in ps:
                tag = "None"
            elif tag not in ps:
                tag = self.get_parent_tag(tag)
            ps = ps.get(tag, ps.get("DEFAULT"))
        elif isinstance(ps, tuple):
            ps = ps[0] if ps else None

        if ps is None or (is_NNP and PRIMARY_STRESS not in (ps or "")):
            ps, rating = self.get_NNP(word)
            if ps is not None:
                return ps, rating

        return apply_stress(ps, stress), rating

    def close(self) -> None:
        self._selected.close()

    def get_special_case(
        self,
        word: str,
        tag: str | None,
        stress: float | None,
        ctx: TokenContext | None,
    ) -> tuple[str | None, int | None]:
        """Handle special case words with context-dependent pronunciations."""
        if tag == "ADD" and word in ADD_SYMBOLS:
            return self.lookup(ADD_SYMBOLS[word], None, -0.5, ctx)
        elif word in SYMBOLS:
            return self.lookup(SYMBOLS[word], None, None, ctx)
        elif (
            "." in word.strip(".")
            and word.replace(".", "").isalpha()
            and len(max(word.split("."), key=len)) < 3
        ):
            return self.get_NNP(word)
        elif word in ("a", "A"):
            return ("ɐ" if tag == "DT" else "ˈA", 4)
        elif word in ("am", "Am", "AM"):
            if tag is not None and tag.startswith("NN"):
                return self.get_NNP(word)
            elif (
                ctx is None
                or ctx.future_vowel is None
                or word != "am"
                or (stress and stress > 0)
            ):
                hit = self._get_hit("am")
                return (
                    hit.value
                    if hit is not None and isinstance(hit.value, str)
                    else None,
                    hit.rating if hit is not None else 4,
                )
            return ("ɐm", 4)
        elif word in ("an", "An", "AN"):
            if word == "AN" and tag is not None and tag.startswith("NN"):
                return self.get_NNP(word)
            return ("ɐn", 4)
        elif word == "I" and tag == "PRP":
            return (f"{SECONDARY_STRESS}I", 4)
        elif word in ("by", "By", "BY") and self.get_parent_tag(tag) == "ADV":
            return ("bˈI", 4)
        elif word in ("to", "To") or (word == "TO" and tag in ("TO", "IN")):
            if ctx is None or ctx.future_vowel is None:
                hit = self._get_hit("to")
                return (
                    hit.value
                    if hit is not None and isinstance(hit.value, str)
                    else None,
                    hit.rating if hit is not None else 4,
                )
            return ("tʊ" if ctx.future_vowel else "tə", 4)
        elif word in ("in", "In") or (word == "IN" and tag != "NNP"):
            stress_mark = (
                PRIMARY_STRESS
                if (ctx is None or ctx.future_vowel is None or tag != "IN")
                else ""
            )
            return (stress_mark + "ɪn", 4)
        elif word in ("the", "The") or (word == "THE" and tag == "DT"):
            return ("ði" if (ctx and ctx.future_vowel) else "ðə", 4)
        elif tag == "IN" and re.match(r"(?i)vs\.?$", word):
            return self.lookup("versus", None, None, ctx)
        elif word in ("used", "Used", "USED"):
            hit = self._get_hit("used")
            used_dict = hit.value if hit is not None else None
            if isinstance(used_dict, Mapping):
                if tag in ("VBD", "JJ") and ctx and ctx.future_to:
                    return (used_dict.get("VBD"), 4)
                return (used_dict.get("DEFAULT"), 4)
        return (None, None)

    # ==========================================================================
    # Suffix handling
    # ==========================================================================

    def _s(self, stem: str | None) -> str | None:
        """Add -s suffix phonemes."""
        if not stem:
            return None
        elif stem[-1] in "ptkfθ":
            return stem + "s"
        elif stem[-1] in "szʃʒʧʤ":
            return stem + ("ɪ" if self.british else "ᵻ") + "z"
        return stem + "z"

    def stem_s(
        self,
        word: str,
        tag: str | None,
        stress: float | None,
        ctx: TokenContext | None,
    ) -> tuple[str | None, int | None]:
        """Handle -s suffix."""
        # Avoid false-positive stemming on proper nouns like "Los"/"Angeles".
        # Allow possessive "'s" even on proper nouns.
        is_possessive = word.endswith("'s")

        # If we have POS info, skip stemming for proper nouns (except possessive).
        if tag in {"NNP", "PROPN"} and not is_possessive:
            return (None, None)

        # If POS is unknown, be conservative: don't stem capitalized tokens
        # (except possessive "'s").
        if tag is None and not word.islower() and not is_possessive:
            return (None, None)

        if len(word) < 3 or not word.endswith("s"):
            return (None, None)

        # Prefer specific suffixes first to reduce accidental matches.
        if (
            len(word) > 4
            and word.endswith("ies")
            and self.is_known(word[:-3] + "y", tag)
        ):
            stem = word[:-3] + "y"
        elif (
            is_possessive
            or (len(word) > 4 and word.endswith("es") and not word.endswith("ies"))
        ) and self.is_known(word[:-2], tag):
            stem = word[:-2]
        elif not word.endswith("ss") and self.is_known(word[:-1], tag):
            stem = word[:-1]
        else:
            return (None, None)

        stem_ps, rating = self.lookup(stem, tag, stress, ctx)
        return (self._s(stem_ps), rating)

    def _ed(self, stem: str | None) -> str | None:
        """Add -ed suffix phonemes."""
        if not stem:
            return None
        elif stem[-1] in "pkfθʃsʧ":
            return stem + "t"
        elif stem[-1] == "d":
            return stem + ("ɪ" if self.british else "ᵻ") + "d"
        elif stem[-1] != "t":
            return stem + "d"
        elif self.british or len(stem) < 2:
            return stem + "ɪd"
        elif stem[-2] in US_TAUS:
            return stem[:-1] + "ɾᵻd"
        return stem + "ᵻd"

    def stem_ed(
        self,
        word: str,
        tag: str | None,
        stress: float | None,
        ctx: TokenContext | None,
    ) -> tuple[str | None, int | None]:
        """Handle -ed suffix."""
        if len(word) < 4 or not word.endswith("d"):
            return (None, None)
        if not word.endswith("dd") and self.is_known(word[:-1], tag):
            stem = word[:-1]
        elif (
            len(word) > 4
            and word.endswith("ed")
            and not word.endswith("eed")
            and self.is_known(word[:-2], tag)
        ):
            stem = word[:-2]
        else:
            return (None, None)
        stem_ps, rating = self.lookup(stem, tag, stress, ctx)
        return (self._ed(stem_ps), rating)

    def _ing(self, stem: str | None) -> str | None:
        """Add -ing suffix phonemes."""
        if not stem:
            return None
        elif self.british:
            if stem[-1] in "əː":
                return None
        elif len(stem) > 1 and stem[-1] == "t" and stem[-2] in US_TAUS:
            return stem[:-1] + "ɾɪŋ"
        return stem + "ɪŋ"

    def stem_ing(
        self,
        word: str,
        tag: str | None,
        stress: float | None,
        ctx: TokenContext | None,
    ) -> tuple[str | None, int | None]:
        """Handle -ing suffix."""
        if len(word) < 5 or not word.endswith("ing"):
            return (None, None)
        if len(word) > 5 and self.is_known(word[:-3], tag):
            stem = word[:-3]
        elif self.is_known(word[:-3] + "e", tag):
            stem = word[:-3] + "e"
        elif (
            len(word) > 5
            and re.search(r"([bcdgklmnprstvxz])\1ing$|cking$", word)
            and self.is_known(word[:-4], tag)
        ):
            stem = word[:-4]
        else:
            return (None, None)
        stem_ps, rating = self.lookup(stem, tag, 0.5 if stress is None else stress, ctx)
        return (self._ing(stem_ps), rating)

    def get_word(
        self,
        word: str,
        tag: str | None,
        stress: float | None,
        ctx: TokenContext | None,
    ) -> tuple[str | None, int | None]:
        """Get phonemes for a word, trying various strategies."""
        # Check special cases first
        ps, rating = self.get_special_case(word, tag, stress, ctx)
        if ps is not None:
            return (ps, rating)

        wl = word.lower()
        # Check if we should lowercase
        if (
            len(word) > 1
            and word.replace("'", "").isalpha()
            and word != word.lower()
            and (tag != "NNP" or len(word) > 7)
            and not self._contains_selected(word)
            and (word == word.upper() or word[1:] == word[1:].lower())
            and (
                self._contains_selected(wl)
                or any(
                    fn(wl, tag, stress, ctx)[0]
                    for fn in (self.stem_s, self.stem_ed, self.stem_ing)
                )
            )
        ):
            word = wl

        if self.is_known(word, tag):
            return self.lookup(word, tag, stress, ctx)
        elif word.endswith("s'") and self.is_known(word[:-2] + "'s", tag):
            return self.lookup(word[:-2] + "'s", tag, stress, ctx)
        elif word.endswith("'") and self.is_known(word[:-1], tag):
            return self.lookup(word[:-1], tag, stress, ctx)

        # Try suffixes
        _s, rating = self.stem_s(word, tag, stress, ctx)
        if _s is not None:
            return (_s, rating)
        _ed, rating = self.stem_ed(word, tag, stress, ctx)
        if _ed is not None:
            return (_ed, rating)
        _ing, rating = self.stem_ing(word, tag, 0.5 if stress is None else stress, ctx)
        if _ing is not None:
            return (_ing, rating)

        return (None, None)

    @staticmethod
    def numeric_if_needed(c: str) -> str:
        """Convert unicode digit to ASCII if needed."""
        if not c.isdigit():
            return c
        n = unicodedata.numeric(c)
        return str(int(n)) if n == int(n) else c

    @staticmethod
    def is_number(word: str, is_head: bool) -> bool:
        """Check if word represents a number."""
        if all(not c.isdigit() for c in word):
            return False
        suffixes = ("ing", "'d", "ed", "'s", *ORDINALS, "s")
        for s in suffixes:
            if word.endswith(s):
                word = word[: -len(s)]
                break
        return all(
            c.isdigit() or c in ",." or (is_head and i == 0 and c == "-")
            for i, c in enumerate(word)
        )

    @staticmethod
    def normalize_greek(word: str) -> str:
        """Convert Greek letters to their English names.

        Args:
            word: Word possibly containing Greek letters.

        Returns:
            Word with Greek letters replaced by their English names.
        """
        # Single Greek letter becomes the letter name
        if word in GREEK_LETTERS:
            return GREEK_LETTERS[word]

        # For words containing Greek letters, replace each occurrence
        result = word
        for greek, english in GREEK_LETTERS.items():
            if greek in result:
                result = result.replace(greek, english)
        return result

    def __call__(
        self,
        word: str,
        tag: str | None = None,
        stress: float | None = None,
        ctx: TokenContext | None = None,
    ) -> tuple[str | None, int | None]:
        """Look up phonemes for a word.

        Args:
            word: Word to look up.
            tag: POS tag.
            stress: Stress level.
            ctx: Token context.

        Returns:
            Tuple of (phonemes, rating) or (None, None) if not found.
        """
        # Normalize the word
        word = word.replace(chr(8216), "'").replace(chr(8217), "'")
        word = unicodedata.normalize("NFKC", word)
        word = "".join(self.numeric_if_needed(c) for c in word)

        # Normalize Greek letters (e.g., α -> alpha, β -> beta)
        word = self.normalize_greek(word)

        # Calculate stress from capitalization
        if stress is None and word != word.lower():
            stress = self.cap_stresses[int(word == word.upper())]

        ps, rating = self.get_word(word, tag, stress, ctx)
        if ps is not None:
            return (apply_stress(ps, stress), rating)

        # Check if it's a number and try number conversion
        if self.is_number(word, True):
            ps, rating = self._convert_number(word, None, True)
            if ps is not None:
                return (apply_stress(ps, stress), rating)

        # Check for valid characters
        if not all(ord(c) in LEXICON_ORDS for c in word):
            return (None, None)

        return (None, None)

    def _convert_number(
        self,
        word: str,
        currency: str | None,
        is_head: bool,
    ) -> tuple[str | None, int | None]:
        """Convert a number to phonemes using num2words.

        Args:
            word: The number string.
            currency: Optional currency symbol.
            is_head: Whether this is the first word.

        Returns:
            Tuple of (phonemes, rating) or (None, None).
        """
        try:
            from kokorog2p.en.numbers import NumberConverter

            converter = NumberConverter(
                lookup_fn=self.lookup,
                stem_s_fn=self.stem_s,
            )
            return converter.convert(word, currency, is_head)
        except ImportError:
            # num2words not installed
            return (None, None)
        except Exception:
            # Conversion failed
            return (None, None)
