"""Lexicon-based G2P lookup for English.

Based on misaki by hexgrad, adapted for kokorog2p.
"""

import importlib.resources
import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Final

from kokorog2p.en import data
from kokorog2p.phonemes import GB_VOCAB, US_VOCAB

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


# =============================================================================
# Stress Functions
# =============================================================================


def apply_stress(ps: str | None, stress: float | None) -> str | None:
    """Apply stress modification to a phoneme string.

    Args:
        ps: Phoneme string.
        stress: Stress level (-2=remove all, -1=demote, 0=neutral,
            1=promote, 2=force primary).

    Returns:
        Modified phoneme string.
    """
    if ps is None or stress is None:
        return ps

    def restress(phonemes: str) -> str:
        """Move stress markers before their associated vowels."""
        ips = list(enumerate(phonemes))
        stresses = {}
        for i, p in ips:
            if p in STRESSES:
                # Find next vowel
                for j, v in ips[i:]:
                    if v in VOWELS:
                        stresses[i] = j
                        break
        for i, j in stresses.items():
            _, s = ips[i]
            ips[i] = (j - 0.5, s)
        return "".join(p for _, p in sorted(ips))

    if stress < -1:
        # Remove all stress
        return ps.replace(PRIMARY_STRESS, "").replace(SECONDARY_STRESS, "")
    elif stress == -1 or (stress in (0, -0.5) and PRIMARY_STRESS in ps):
        # Demote primary to secondary
        return ps.replace(SECONDARY_STRESS, "").replace(
            PRIMARY_STRESS, SECONDARY_STRESS
        )
    elif stress in (0, 0.5, 1) and all(s not in ps for s in STRESSES):
        # Add secondary stress if missing
        if all(v not in ps for v in VOWELS):
            return ps
        return restress(SECONDARY_STRESS + ps)
    elif stress >= 1 and PRIMARY_STRESS not in ps and SECONDARY_STRESS in ps:
        # Promote secondary to primary
        return ps.replace(SECONDARY_STRESS, PRIMARY_STRESS)
    elif stress > 1 and all(s not in ps for s in STRESSES):
        # Add primary stress
        if all(v not in ps for v in VOWELS):
            return ps
        return restress(PRIMARY_STRESS + ps)
    return ps


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
        self.golds: dict[str, str | dict[str, str | None]] = {}
        self.silvers: dict[str, str] = {}

        # Load dictionaries
        prefix = "gb" if british else "us"

        # Only load gold tier if requested
        if load_gold:
            files = importlib.resources.files(data)
            with (files / f"{prefix}_gold.json").open("r", encoding="utf-8") as r:
                self.golds = self._grow_dictionary(json.load(r))

        # Only load silver tier if requested
        if load_silver:
            files = importlib.resources.files(data)
            with (files / f"{prefix}_silver.json").open("r", encoding="utf-8") as r:
                self.silvers = self._grow_dictionary(json.load(r))

        # Validate vocabulary (only if gold dictionary is loaded)
        if load_gold:
            vocab = GB_VOCAB if british else US_VOCAB
            for word, ps in self.golds.items():
                if isinstance(ps, str):
                    assert all(
                        c in vocab for c in ps
                    ), f"Invalid phoneme in {word}: {ps}"
                else:
                    assert "DEFAULT" in ps, f"Missing DEFAULT in {word}"
                    for v in ps.values():
                        if v is not None:
                            assert all(
                                c in vocab for c in v
                            ), f"Invalid phoneme in {word}: {v}"

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
        elif tag.startswith("ADV") or tag.startswith("RB"):
            return "ADV"
        elif tag.startswith("ADJ") or tag.startswith("JJ"):
            return "ADJ"
        return tag

    def is_known(self, word: str, tag: str | None = None) -> bool:
        """Check if a word is in the lexicon."""
        if word in self.golds or word in SYMBOLS or word in self.silvers:
            return True
        elif not word.isalpha() or not all(ord(c) in LEXICON_ORDS for c in word):
            return False
        elif len(word) == 1:
            return True
        elif word == word.upper() and word.lower() in self.golds:
            return True
        return word[1:] == word[1:].upper()

    def get_NNP(self, word: str) -> tuple[str | None, int | None]:
        """Get phonemes for a proper noun by spelling."""
        ps = [self.golds.get(c.upper()) for c in word if c.isalpha()]
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
        if word == word.upper() and word not in self.golds:
            word = word.lower()
            is_NNP = tag == "NNP"

        ps: str | None = self.golds.get(word)  # type: ignore
        rating = 4
        if ps is None and not is_NNP:
            ps = self.silvers.get(word)
            rating = 3

        if isinstance(ps, dict):
            if ctx and ctx.future_vowel is None and "None" in ps:  # type: ignore[unreachable]
                tag = "None"
            elif tag not in ps:
                tag = self.get_parent_tag(tag)
            ps = ps.get(tag, ps["DEFAULT"])  # type: ignore

        if ps is None or (is_NNP and PRIMARY_STRESS not in (ps or "")):
            ps, rating = self.get_NNP(word)
            if ps is not None:
                return ps, rating

        return apply_stress(ps, stress), rating

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
                gold = self.golds.get("am")
                return (gold if isinstance(gold, str) else None, 4)
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
                gold = self.golds.get("to")
                return (gold if isinstance(gold, str) else None, 4)
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
            used_dict = self.golds.get("used")
            if isinstance(used_dict, dict):
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
            and word not in self.golds
            and word not in self.silvers
            and (word == word.upper() or word[1:] == word[1:].lower())
            and (
                wl in self.golds
                or wl in self.silvers
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
