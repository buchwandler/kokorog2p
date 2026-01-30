"""Number-to-words conversion for English G2P.

This module provides functions to convert numbers (digits, decimals, ordinals,
years, currency) into their word representations for text-to-speech.

Based on misaki by hexgrad, adapted for kokorog2p.
"""

import re
from collections.abc import Callable

# Proper thousands grouping like 30,000 or 1,234,567.89
_THOUSANDS_GROUPED_RE = re.compile(r"^\d{1,3}(?:,\d{3})+(?:\.\d+)?$")

_THOUSANDS_INT_RE = re.compile(r"^\d{1,3}(?:,\d{3})*$")
# Ordinal suffixes
ORDINALS = frozenset(["st", "nd", "rd", "th"])

# Currency symbols and their word forms
CURRENCIES = {
    "$": ("dollar", "cent"),
    "£": ("pound", "pence"),
    "€": ("euro", "cent"),
}


def is_digit(text: str) -> bool:
    """Check if text consists only of digits."""
    return bool(re.match(r"^[0-9]+$", text))


def is_currency_amount(word: str) -> bool:
    """Check if word looks like a currency amount (e.g., '12.99', '30,000.10').

    Rules:
    - Optional thousands separators, but only valid grouping (1,234,567)
    - Optional decimal part (.<digits>)
    - Reject invalid grouping like '12,34' or '1,23,456'
    - Allow leading-decimal amounts like '.50'
    """
    if not word:
        return False

    # Handle leading-decimal like ".50"
    if word.startswith("."):
        return len(word) > 1 and word[1:].isdigit()

    # Split integer/decimal parts (only one dot allowed)
    parts = word.split(".")
    if len(parts) > 2:
        return False

    int_part = parts[0]
    frac_part = parts[1] if len(parts) == 2 else None

    # Validate fractional part if present
    if frac_part is not None and frac_part and not frac_part.isdigit():
        return False
    if frac_part is not None and frac_part == "":
        # trailing dot like "12." -> treat as invalid for currency amounts
        return False

    # Validate integer part with or without commas
    if "," in int_part:
        if not _THOUSANDS_INT_RE.match(int_part):
            return False
    else:
        if not int_part.isdigit():
            return False

    return True


class NumberConverter:
    """Convert numbers to their word representations.

    This class handles various number formats including:
    - Cardinal numbers (1, 2, 3 -> one, two, three)
    - Ordinal numbers (1st, 2nd -> first, second)
    - Years (1984 -> nineteen eighty-four)
    - Decimals (3.14 -> three point one four)
    - Currency ($12.50 -> twelve dollars and fifty cents)
    """

    def __init__(
        self,
        lookup_fn: Callable[
            [str, str | None, float | None, object | None],
            tuple[str | None, int | None],
        ],
        stem_s_fn: Callable[
            [str, str | None, float | None, object | None],
            tuple[str | None, int | None],
        ],
    ) -> None:
        """Initialize the number converter.

        Args:
            lookup_fn: Function to look up words in the lexicon.
            stem_s_fn: Function to add -s suffix to words.
        """
        self.lookup = lookup_fn
        self.stem_s = stem_s_fn
        self._num2words: Callable | None = None

    @property
    def num2words(self) -> Callable:
        """Lazily import num2words."""
        if self._num2words is None:
            from num2words import num2words

            self._num2words = num2words
        return self._num2words

    def _extend_num(
        self,
        num: str,
        result: list[tuple[str, int]],
        num_flags: set,
        first: bool = True,
        escape: bool = False,
    ) -> None:
        """Extend result with words for a number."""
        if escape:
            splits = re.split(r"[^a-z]+", num)
        else:
            try:
                splits = re.split(r"[^a-z]+", self.num2words(int(num)))
            except (ValueError, OverflowError):
                splits = [num]

        for i, w in enumerate(splits):
            if not w:
                continue
            if w != "and" or "&" in num_flags:
                if (
                    first
                    and i == 0
                    and len(splits) > 1
                    and w == "one"
                    and "a" in num_flags
                ):
                    result.append(("ə", 4))
                else:
                    ps = self.lookup(w, None, -2 if w == "point" else None, None)
                    if ps[0]:
                        result.append(ps)  # type: ignore
            elif w == "and" and "n" in num_flags and result:
                # Contract "and" to "n" sound
                last_ps, last_rating = result[-1]
                result[-1] = (last_ps + "ən", last_rating)

    def _convert_ordinal(
        self, word: str, result: list[tuple[str, int]], num_flags: set
    ) -> bool:
        """Convert ordinal number (1st, 2nd, etc.). Returns True if handled."""
        try:
            ordinal_word = self.num2words(int(word), to="ordinal")
            self._extend_num(ordinal_word, result, num_flags, escape=True)
            return True
        except (ValueError, OverflowError):
            return False

    def _convert_year(
        self, word: str, result: list[tuple[str, int]], num_flags: set
    ) -> bool:
        """Convert 4-digit year. Returns True if handled."""
        try:
            year_word = self.num2words(int(word), to="year")
            self._extend_num(year_word, result, num_flags, escape=True)
            return True
        except (ValueError, OverflowError):
            return False

    def _convert_phone_sequence(
        self, word: str, result: list[tuple[str, int]], num_flags: set
    ) -> None:
        """Convert phone numbers and sequences (not at head, no decimal)."""
        num = word.replace(",", "")
        if num[0] == "0" or len(num) > 3:
            # Read digit by digit
            for n in num:
                self._extend_num(n, result, num_flags, first=False)
        elif len(num) == 3 and not num.endswith("00"):
            # Three-digit numbers like "305" -> "three oh five"
            self._extend_num(num[0], result, num_flags)
            if num[1] == "0":
                o_ps = self.lookup("O", None, -2, None)
                if o_ps[0]:
                    result.append(o_ps)  # type: ignore
                self._extend_num(num[2], result, num_flags, first=False)
            else:
                self._extend_num(num[1:], result, num_flags, first=False)
        else:
            self._extend_num(num, result, num_flags)

    def _convert_dotted_sequence(
        self, word: str, result: list[tuple[str, int]], num_flags: set, is_head: bool
    ) -> None:
        """Convert IP addresses and version numbers (multiple dots)."""
        first = True
        for num in word.replace(",", "").split("."):
            if not num:
                pass
            elif num[0] == "0" or (len(num) != 2 and any(n != "0" for n in num[1:])):
                for n in num:
                    self._extend_num(n, result, num_flags, first=False)
            else:
                self._extend_num(num, result, num_flags, first=first)
            first = False

    def _convert_currency(
        self, word: str, currency: str, result: list[tuple[str, int]], num_flags: set
    ) -> None:
        """Convert currency amounts."""
        pairs = []
        parts = word.replace(",", "").split(".")
        currency_names = CURRENCIES[currency]
        for i, part in enumerate(parts):
            if part:
                pairs.append(
                    (
                        int(part),
                        currency_names[i] if i < len(currency_names) else "",
                    )
                )

        # Remove zero amounts
        if len(pairs) > 1:
            if pairs[1][0] == 0:
                pairs = pairs[:1]
            elif pairs[0][0] == 0:
                pairs = pairs[1:]

        for i, (num, unit) in enumerate(pairs):
            if i > 0:
                and_ps = self.lookup("and", None, None, None)
                if and_ps[0]:
                    result.append(and_ps)  # type: ignore
            self._extend_num(str(num), result, num_flags, first=i == 0)

            # Add currency unit (pluralized if needed)
            if unit:
                if abs(num) != 1 and unit != "pence":
                    unit_ps = self.stem_s(unit + "s", None, None, None)
                else:
                    unit_ps = self.lookup(unit, None, None, None)
                if unit_ps[0]:
                    result.append(unit_ps)  # type: ignore

    def _convert_regular_number(
        self,
        word: str,
        suffix: str | None,
        result: list[tuple[str, int]],
        num_flags: set,
    ) -> bool:
        """Convert regular numbers. Returns True if handled."""
        try:
            if is_digit(word):
                word_text = self.num2words(int(word), to="cardinal")
            elif "." not in word:
                to_type = "ordinal" if suffix in ORDINALS else "cardinal"
                word_text = self.num2words(int(word.replace(",", "")), to=to_type)
            else:
                word = word.replace(",", "")
                if word[0] == ".":
                    # Decimal starting with point: ".5" -> "point five"
                    word_text = "point " + " ".join(
                        self.num2words(int(n)) for n in word[1:]
                    )
                else:
                    word_text = self.num2words(float(word))
            self._extend_num(word_text, result, num_flags, escape=True)
            return True
        except (ValueError, OverflowError):
            return False

    def convert(
        self,
        word: str,
        currency: str | None = None,
        is_head: bool = True,
        num_flags: set | None = None,
    ) -> tuple[str | None, int | None]:
        """Convert a number to its word representation.

        Args:
            word: The number string to convert.
            currency: Optional currency symbol (e.g., '$', '£').
            is_head: Whether this is the first word in a phrase.
            num_flags: Optional flags for number formatting.

        Returns:
            Tuple of (phonemes, rating) or (None, None) if conversion failed.
        """
        if num_flags is None:
            num_flags = set()

        # Extract suffix (e.g., "1st" -> "1", "st")
        suffix_match = re.search(r"[a-z']+$", word)
        suffix = suffix_match.group() if suffix_match else None
        word = word[: -len(suffix)] if suffix else word

        result: list[tuple[str, int]] = []

        # Handle negative numbers
        if word.startswith("-"):
            minus_ps = self.lookup("minus", None, None, None)
            if minus_ps[0]:
                result.append(minus_ps)  # type: ignore
            word = word[1:]

        # If it's explicitly thousands-grouped (e.g. 30,000), treat it as a real
        # cardinal/decimal/currency amount even if it isn't at the head.
        grouped_amount = bool(_THOUSANDS_GROUPED_RE.match(word))

        # Handle ordinals (1st, 2nd, etc.)
        if is_digit(word) and suffix in ORDINALS:
            if not self._convert_ordinal(word, result, num_flags):
                return (None, None)

        # Handle years (4-digit numbers without currency)
        elif (
            not result
            and len(word) == 4
            and currency not in CURRENCIES
            and is_digit(word)
        ):
            if not self._convert_year(word, result, num_flags):
                return (None, None)

        # Handle phone numbers and sequences (not at head, no decimal)
        elif not grouped_amount and not is_head and "." not in word:
            self._convert_phone_sequence(word, result, num_flags)

        # Handle IP addresses and version numbers (multiple dots)
        elif word.count(".") > 1 or (not grouped_amount and not is_head):
            self._convert_dotted_sequence(word, result, num_flags, is_head)

        # Handle currency amounts
        elif currency in CURRENCIES and is_currency_amount(word):
            self._convert_currency(word, currency, result, num_flags)

        # Handle regular numbers
        else:
            if not self._convert_regular_number(word, suffix, result, num_flags):
                return (None, None)

        if not result:
            return (None, None)

        # Combine results
        phonemes = " ".join(p for p, _ in result)
        rating = min(r for _, r in result)

        # Handle suffixes
        if suffix in ("s", "'s"):
            return self._add_s(phonemes), rating
        elif suffix in ("ed", "'d"):
            return self._add_ed(phonemes), rating
        elif suffix == "ing":
            return self._add_ing(phonemes), rating

        return phonemes, rating

    def _add_s(self, stem: str | None) -> str | None:
        """Add -s suffix phonemes."""
        if not stem:
            return None
        if stem[-1] in "ptkfθ":
            return stem + "s"
        elif stem[-1] in "szʃʒʧʤ":
            return stem + "ᵻz"
        return stem + "z"

    def _add_ed(self, stem: str | None) -> str | None:
        """Add -ed suffix phonemes."""
        if not stem:
            return None
        if stem[-1] in "pkfθʃsʧ":
            return stem + "t"
        elif stem[-1] == "d":
            return stem + "ᵻd"
        elif stem[-1] != "t":
            return stem + "d"
        return stem + "ᵻd"

    def _add_ing(self, stem: str | None) -> str | None:
        """Add -ing suffix phonemes."""
        if not stem:
            return None
        return stem + "ɪŋ"

    def append_currency(self, phonemes: str, currency: str | None) -> str:
        """Append currency word to phonemes.

        Args:
            phonemes: The phoneme string.
            currency: Currency symbol.

        Returns:
            Phonemes with currency word appended.
        """
        if not currency:
            return phonemes
        currency_info = CURRENCIES.get(currency)
        if not currency_info:
            return phonemes
        currency_ps = self.stem_s(currency_info[0] + "s", None, None, None)
        if currency_ps[0]:
            return f"{phonemes} {currency_ps[0]}"
        return phonemes
