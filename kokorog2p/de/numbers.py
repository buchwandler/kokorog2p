"""Deterministic German number parsing and text expansion."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from kokorog2p.de.text_rules import (
    MONTH_NAMES,
    MONTHS,
    NUMBERED_UNITS,
    NumberedUnit,
)

ORDINALS = frozenset([".", "te", "ter", "tes", "ten", "tem"])
CURRENCIES = {
    "€": ("Euro", "Cent"),
    "EUR": ("Euro", "Cent"),
    "$": ("Dollar", "Cent"),
    "£": ("Pfund", "Pence"),
    "CHF": ("Franken", "Rappen"),
}

_DIGIT_WORDS = (
    "null",
    "eins",
    "zwei",
    "drei",
    "vier",
    "fünf",
    "sechs",
    "sieben",
    "acht",
    "neun",
)
_TEENS = (
    "zehn",
    "elf",
    "zwölf",
    "dreizehn",
    "vierzehn",
    "fünfzehn",
    "sechzehn",
    "siebzehn",
    "achtzehn",
    "neunzehn",
)
_TENS = (
    "",
    "",
    "zwanzig",
    "dreißig",
    "vierzig",
    "fünfzig",
    "sechzig",
    "siebzig",
    "achtzig",
    "neunzig",
)


def is_digit(text: str) -> bool:
    """Return whether *text* contains only ASCII digits."""

    return bool(re.fullmatch(r"[0-9]+", text))


def _normalized_number_text(value: str) -> str | None:
    value = value.strip()
    if value.startswith(("+", "-")):
        sign, value = value[0], value[1:]
    else:
        sign = ""
    if not value:
        return None
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
        value = value.replace(".", "")
    elif not re.fullmatch(r"\d+", value):
        return None
    return sign + value


def is_currency_amount(word: str) -> bool:
    """Return whether *word* is a valid German-style amount."""

    candidate = word.strip().lstrip("+-")
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", candidate):
        return True
    return bool(re.fullmatch(r"\d+(?:[,.]\d+)?|[,.]\d+", candidate))


def _under_thousand(n: int) -> str:
    if n < 10:
        return _DIGIT_WORDS[n]
    if n < 20:
        return _TEENS[n - 10]
    if n < 100:
        return (
            _TENS[n // 10]
            if n % 10 == 0
            else _DIGIT_WORDS[n % 10].replace("eins", "ein") + "und" + _TENS[n // 10]
        )
    hundreds, remainder = divmod(n, 100)
    prefix = "einhundert" if hundreds == 1 else _DIGIT_WORDS[hundreds] + "hundert"
    return prefix + (_under_thousand(remainder) if remainder else "")


def number_to_german(n: int) -> str:
    """Convert an integer to deterministic German cardinal words."""

    if n < 0:
        return "minus " + number_to_german(-n)
    if n < 1000:
        return _under_thousand(n)
    if n < 1_000_000:
        thousands, remainder = divmod(n, 1000)
        prefix = (
            "eintausend" if thousands == 1 else number_to_german(thousands) + "tausend"
        )
        return prefix + (number_to_german(remainder) if remainder else "")
    if n < 1_000_000_000:
        millions, remainder = divmod(n, 1_000_000)
        prefix = (
            "eine Million"
            if millions == 1
            else number_to_german(millions) + " Millionen"
        )
        return prefix + (" " + number_to_german(remainder) if remainder else "")
    if n < 1_000_000_000_000:
        billions, remainder = divmod(n, 1_000_000_000)
        prefix = (
            "eine Milliarde"
            if billions == 1
            else number_to_german(billions) + " Milliarden"
        )
        return prefix + (" " + number_to_german(remainder) if remainder else "")
    return str(n)


def ordinal_to_german(n: int) -> str:
    """Convert an integer to a basic German ordinal form."""

    if n <= 0:
        return str(n) + "."
    special = {1: "erste", 3: "dritte", 7: "siebte", 8: "achte"}
    if n in special:
        return special[n]
    return number_to_german(n) + ("te" if n < 20 else "ste")


def _decimal_parts(value: str) -> tuple[str, str] | None:
    value = value.strip().lstrip("+-")
    if not value:
        return None
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+,\d+", value):
        integer, fraction = value.split(",", 1)
        return integer.replace(".", ""), fraction
    if "," in value:
        integer, fraction = value.split(",", 1)
        if not integer:
            integer = "0"
        return (
            integer if integer.isdigit() else None,
            fraction if fraction.isdigit() else None,
        )  # type: ignore[return-value]
    if value.count(".") == 1:
        integer, fraction = value.split(".", 1)
        if integer.isdigit() and fraction.isdigit() and len(fraction) <= 2:
            return integer, fraction
    if value.startswith(".") and value[1:].isdigit():
        return "0", value[1:]
    if value.isdigit():
        return value, ""
    return None


class GermanNumberConverter:
    """Convert German numeric forms without optional runtime dependencies."""

    def __init__(
        self, lookup_fn: Callable[[str, str | None], str | None] | None = None
    ) -> None:
        self.lookup = lookup_fn
        self._num2words: Callable | None = None

    @property
    def num2words(self) -> Callable:
        """Compatibility callable retained for callers of the old API."""

        if self._num2words is None:
            self._num2words = lambda n, to="cardinal": (
                ordinal_to_german(int(n))
                if to == "ordinal"
                else number_to_german(int(n))
            )
        return self._num2words

    def convert_cardinal(self, word: str) -> str:
        normalized = _normalized_number_text(word)
        if normalized is None:
            return word
        try:
            return number_to_german(int(normalized))
        except (ValueError, OverflowError):
            return word

    def convert_ordinal(self, word: str) -> str:
        normalized = _normalized_number_text(word.rstrip("."))
        if normalized is None:
            return word
        try:
            return ordinal_to_german(int(normalized))
        except (ValueError, OverflowError):
            return word

    def convert_year(self, word: str) -> str:
        try:
            year = int(word)
        except ValueError:
            return word
        if 1100 <= year <= 1999:
            century, remainder = divmod(year, 100)
            return (
                number_to_german(century)
                + "hundert"
                + (number_to_german(remainder) if remainder else "")
            )
        return number_to_german(year)

    def convert_decimal(self, word: str) -> str:
        sign = "minus " if word.strip().startswith("-") else ""
        parts = _decimal_parts(word)
        if parts is None:
            return word
        integer, fraction = parts
        if not fraction:
            return sign + self.convert_cardinal(integer)
        return (
            sign
            + self.convert_cardinal(integer)
            + " Komma "
            + " ".join(_DIGIT_WORDS[int(d)] for d in fraction)
        )

    def convert_currency(self, word: str, currency: str) -> str:
        sign = "minus " if word.strip().startswith("-") else ""
        candidate = word.strip().lstrip("+-")
        parts = _decimal_parts(candidate)
        if parts is None:
            return word
        integer, fraction = parts
        names = CURRENCIES.get(currency, ("", ""))
        integer_word = self.convert_cardinal(integer)
        if integer_word == "eins":
            integer_word = "ein"
        result = [integer_word, names[0]]
        if fraction and int(fraction) > 0:
            cents = (fraction + "0")[:2]
            result.extend((self.convert_cardinal(cents), names[1]))
        return sign + " ".join(result)

    def convert(
        self,
        word: str,
        currency: str | None = None,
        is_ordinal: bool = False,
        is_year: bool = False,
    ) -> str:
        if is_ordinal:
            return self.convert_ordinal(word)
        if currency and currency in CURRENCIES:
            return self.convert_currency(word, currency)
        if is_year and re.fullmatch(r"\d{4}", word):
            return self.convert_year(word)
        if _decimal_parts(word) and ("," in word or "." in word):
            return self.convert_decimal(word)
        return self.convert_cardinal(word)


_NUMBER = r"-?(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[,.]\d+)?|[,.]\d+)"
_UNIT_ALTERNATIVE = "|".join(unit.pattern for unit in NUMBERED_UNITS)
_UNIT_PATTERN = re.compile(
    rf"(?<!\w)(?P<number>{_NUMBER})\s*(?P<unit>{_UNIT_ALTERNATIVE})(?!\w)"
)
_CURRENCY_SUFFIX = re.compile(
    rf"(?<!\w)(?P<number>{_NUMBER})\s*(?P<currency>EUR|€|\$|£|CHF)(?!\w)"
)
_CURRENCY_PREFIX = re.compile(
    rf"(?<!\w)(?P<currency>EUR|€|\$|£|CHF)\s*(?P<number>{_NUMBER})(?!\w)"
)
_TEMPERATURE = re.compile(rf"(?<!\w)(?P<number>{_NUMBER})\s*°\s*(?P<unit>[CFcf])(?!\w)")
_TIME = re.compile(
    r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>\d{2})(?P<suffix>\s*Uhr)?(?!\w)"
)
_DATE_NUMERIC = re.compile(
    r"(?<!\w)(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{2,4})(?!\w)"
)
_CONTEXTUAL_DATE_NUMERIC = re.compile(
    r"(?P<prefix>(?<!\w)(?i:am|zum|vom)\s+)"
    r"(?P<day>\d{1,2})\.(?P<month>\d{1,2})\.(?P<year>\d{2,4})(?!\w)"
)
_DATE_TEXT = re.compile(
    r"(?<!\w)(?P<day>\d{1,2})\.\s*(?P<month>[A-Za-zÄÖÜäöü]+)\.?\s+(?P<year>\d{4})(?!\w)",
    re.IGNORECASE,
)
_CONTEXTUAL_DATE_TEXT = re.compile(
    r"(?P<prefix>(?<!\w)(?i:am|zum|vom)\s+)"
    r"(?P<day>\d{1,2})\.\s*(?P<month>[A-Za-zÄÖÜäöü]+)\.?\s+"
    r"(?P<year>\d{4})(?!\w)"
)
_INVALID_DATE = re.compile(r"(?<!\w)\d{1,2}\.\d{1,2}\.\d{2,4}(?!\w)")
_INVALID_TIME = re.compile(r"(?<!\w)\d{1,2}:\d{2}(?!\w)")
_LABEL_NUMBER = re.compile(
    r"(?P<label>Nummer|laufende Nummer|Gleis|Kapitel|Absatz|Seite)"
    r"(?P<space>\s+)(?P<number>\d+)(?P<period>\.)?",
    re.IGNORECASE,
)
_CONTEXTUAL_ORDINAL = re.compile(
    r"(?P<prefix>\b(?i:am|im|zum|zur|vom|der|die|das|den|dem|des|"
    r"auf\s+die|auf\s+der|auf\s+dem|in\s+der|in\s+dem)\s+)"
    r"(?P<number>\d{1,3})\.\s+"
    r"(?P<noun>[A-ZÄÖÜ][A-Za-zÄÖÜäöüß-]*)\b"
)
_GENERIC_NUMBER = re.compile(
    r"(?<![\w:])(?P<number>-?(?:\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[,.]\d+|\.\d{1,2})?|[,.]\d+))(?![\w:])"
)


def _decimal_value(value: str) -> Decimal | None:
    parts = _decimal_parts(value)
    if parts is None:
        normalized = _normalized_number_text(value)
        if normalized is None:
            return None
        return Decimal(normalized)
    return Decimal(f"{parts[0]}.{parts[1]}")


def _unit_words(
    number: str, unit: NumberedUnit, converter: GermanNumberConverter
) -> str:
    value = _decimal_value(number)
    if value is None:
        return number
    singular = abs(value) == Decimal(1)
    if singular:
        article = "eine" if unit.gender == "f" else "ein"
        if number.startswith("-"):
            return "minus " + article + " " + unit.singular
        return article + " " + unit.singular
    numeric = (
        converter.convert_decimal(number)
        if (
            "," in number
            or ("." in number and not re.fullmatch(r"\d{1,3}(?:\.\d{3})+", number))
        )
        else converter.convert_cardinal(number)
    )
    return numeric + " " + unit.plural


def _unit_replacer(match: re.Match, converter: GermanNumberConverter) -> str:
    unit_text = match.group("unit")
    unit = next(
        (
            candidate
            for candidate in NUMBERED_UNITS
            if re.fullmatch(candidate.pattern, unit_text, candidate.flags)
        ),
        None,
    )
    if unit is None:
        return match.group(0)
    replacement = _unit_words(match.group("number"), unit, converter)
    if (
        unit.dotted
        and match.end() == len(match.string)
        and not match.string.endswith("..")
    ):
        replacement += "."
    return replacement


def _ordinal_with_ending(number: int, ending: str = "e") -> str:
    ordinal = ordinal_to_german(number)
    if not ordinal.endswith("e"):
        return ordinal + ending
    return ordinal[:-1] + ending


def _date_words(
    day: int,
    month: int,
    year: int,
    converter: GermanNumberConverter,
    *,
    ordinal_ending: str = "e",
) -> str:
    try:
        date(year, month, day)
    except ValueError:
        return ""
    month_name = MONTH_NAMES[month - 1]
    ordinal = _ordinal_with_ending(day, ordinal_ending)
    return f"{ordinal} {month_name} {converter.convert_year(str(year))}"


def _text_date_replacer(
    match: re.Match,
    converter: GermanNumberConverter,
    *,
    ordinal_ending: str = "e",
) -> str:
    month_name = MONTHS.get(match.group("month").rstrip(".").lower())
    if month_name is None:
        return match.group(0)
    month_number = MONTH_NAMES.index(month_name) + 1
    result = _date_words(
        int(match.group("day")),
        month_number,
        int(match.group("year")),
        converter,
        ordinal_ending=ordinal_ending,
    )
    return result or match.group(0)


def _contextual_text_date_replacer(
    match: re.Match, converter: GermanNumberConverter
) -> str:
    result = _text_date_replacer(match, converter, ordinal_ending="en")
    if result == match.group(0):
        return result
    return match.group("prefix") + result


def _numeric_date_replacer(match: re.Match, converter: GermanNumberConverter) -> str:
    year = int(match.group("year"))
    year += 2000 if year < 100 else 0
    result = _date_words(
        int(match.group("day")), int(match.group("month")), year, converter
    )
    return result or match.group(0)


def _contextual_numeric_date_replacer(
    match: re.Match, converter: GermanNumberConverter
) -> str:
    year = int(match.group("year"))
    year += 2000 if year < 100 else 0
    result = _date_words(
        int(match.group("day")),
        int(match.group("month")),
        year,
        converter,
        ordinal_ending="en",
    )
    return match.group("prefix") + result if result else match.group(0)


def _numeric_date_is_valid(match: re.Match) -> bool:
    day_text, month_text, year_text = match.group(0).split(".")
    year = int(year_text)
    year += 2000 if year < 100 else 0
    try:
        date(year, int(month_text), int(day_text))
    except ValueError:
        return False
    return True


def _time_replacer(match: re.Match, converter: GermanNumberConverter) -> str:
    hour, minute = int(match.group("hour")), int(match.group("minute"))
    if hour > 23 or minute > 59:
        return match.group(0)
    hour_word = converter.convert_cardinal(str(hour)).replace("eins", "ein")
    minute_word = converter.convert_cardinal(str(minute))
    return f"{hour_word} Uhr" if minute == 0 else f"{hour_word} Uhr {minute_word}"


def _time_is_valid(match: re.Match) -> bool:
    hour_text, minute_text = match.group(0).split(":", 1)
    return int(hour_text) <= 23 and int(minute_text) <= 59


def _temperature_replacer(match: re.Match, converter: GermanNumberConverter) -> str:
    number = match.group("number")
    number_words = (
        converter.convert_decimal(number)
        if (
            "," in number
            or "." in number
            and not re.fullmatch(r"\d{1,3}(?:\.\d{3})+", number)
        )
        else converter.convert_cardinal(number)
    )
    if number_words == "eins":
        number_words = "ein"
    unit_name = "Celsius" if match.group("unit").upper() == "C" else "Fahrenheit"
    return f"{number_words} Grad {unit_name}"


def _label_replacer(match: re.Match, converter: GermanNumberConverter) -> str:
    label = match.group("label")
    if label.lower() == "laufende nummer":
        label = "laufende Nummer"
    elif label and label[0].isupper():
        label = label[0].upper() + label[1:].lower()
    number = converter.convert_cardinal(match.group("number"))
    period = match.group("period") or ""
    return f"{label}{match.group('space')}{number}{period}"


def _contextual_ordinal_replacer(
    match: re.Match, converter: GermanNumberConverter
) -> str:
    prefix = match.group("prefix")
    normalized_prefix = " ".join(prefix.lower().split())
    weak_ending_prefixes = {
        "am",
        "im",
        "zum",
        "zur",
        "vom",
        "den",
        "dem",
        "des",
        "auf der",
        "auf dem",
        "in der",
        "in dem",
    }
    ending = "en" if normalized_prefix in weak_ending_prefixes else "e"
    ordinal = _ordinal_with_ending(int(match.group("number")), ending)
    return f"{prefix}{ordinal} {match.group('noun')}"


def expand_structured_numbers(text: str) -> str:
    """Expand structured German expressions in safe classification order."""

    if not text:
        return text
    converter = GermanNumberConverter()
    protected: dict[str, str] = {}

    def protect_invalid(pattern: re.Pattern, value: re.Match) -> str:
        token = f"\ue000{chr(0xE100 + len(protected))}\ue001"
        protected[token] = value.group(0)
        return token

    text = _INVALID_DATE.sub(
        lambda m: (
            protect_invalid(_INVALID_DATE, m)
            if not _numeric_date_is_valid(m)
            else m.group(0)
        ),
        text,
    )
    text = _INVALID_TIME.sub(
        lambda m: (
            protect_invalid(_INVALID_TIME, m) if not _time_is_valid(m) else m.group(0)
        ),
        text,
    )
    text = _CURRENCY_SUFFIX.sub(
        lambda m: converter.convert_currency(m.group("number"), m.group("currency")),
        text,
    )
    text = _CURRENCY_PREFIX.sub(
        lambda m: converter.convert_currency(m.group("number"), m.group("currency")),
        text,
    )
    text = _UNIT_PATTERN.sub(lambda m: _unit_replacer(m, converter), text)
    text = _TEMPERATURE.sub(lambda m: _temperature_replacer(m, converter), text)
    text = _CONTEXTUAL_DATE_NUMERIC.sub(
        lambda m: _contextual_numeric_date_replacer(m, converter), text
    )
    text = _DATE_NUMERIC.sub(lambda m: _numeric_date_replacer(m, converter), text)
    text = _CONTEXTUAL_DATE_TEXT.sub(
        lambda m: _contextual_text_date_replacer(m, converter), text
    )
    text = _DATE_TEXT.sub(lambda m: _text_date_replacer(m, converter), text)
    text = _TIME.sub(lambda m: _time_replacer(m, converter), text)
    text = _LABEL_NUMBER.sub(lambda m: _label_replacer(m, converter), text)
    text = _CONTEXTUAL_ORDINAL.sub(
        lambda m: _contextual_ordinal_replacer(m, converter), text
    )

    def generic_replacer(match: re.Match) -> str:
        number = match.group("number")
        if "," in number or (
            number.count(".") == 1 and len(number.rsplit(".", 1)[1]) <= 2
        ):
            return converter.convert_decimal(number)
        if re.fullmatch(r"\d{4}", number) and 1100 <= int(number) <= 2999:
            return converter.convert_year(number)
        return converter.convert_cardinal(number)

    text = _GENERIC_NUMBER.sub(generic_replacer, text)
    for token, original in protected.items():
        text = text.replace(token, original)
    return text


def expand_number(text: str) -> str:
    """Expand numbers and structured numeric expressions in *text*."""

    return expand_structured_numbers(text)
