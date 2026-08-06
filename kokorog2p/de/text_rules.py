"""Data-only rules for structured German text normalization.

The regular abbreviation expander is intentionally kept for lexical forms.
Measurement symbols belong here because they only have an unambiguous meaning
when they are attached to a number.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Gender = Literal["f", "m", "n"]


@dataclass(frozen=True)
class NumberedUnit:
    """A number-dependent German unit spelling."""

    pattern: str
    singular: str
    plural: str
    gender: Gender | None = None
    flags: int = 0
    dotted: bool = False


# Longest and most specific symbols must precede their shorter aliases.
NUMBERED_UNITS = (
    NumberedUnit(r"kWh", "Kilowattstunde", "Kilowattstunden", "f"),
    NumberedUnit(r"mAh", "Milliamperestunde", "Milliamperestunden", "f"),
    NumberedUnit(r"GHz", "Gigahertz", "Gigahertz"),
    NumberedUnit(r"MHz", "Megahertz", "Megahertz"),
    NumberedUnit(r"kHz", "Kilohertz", "Kilohertz"),
    NumberedUnit(r"Wh", "Wattstunde", "Wattstunden", "f"),
    NumberedUnit(r"mA", "Milliampere", "Milliampere"),
    NumberedUnit(r"m3|m³", "Kubikmeter", "Kubikmeter"),
    NumberedUnit(
        r"Stck\.",
        "Stück",
        "Stück",
        "n",
        flags=re.IGNORECASE,
        dotted=True,
    ),
    NumberedUnit(r"ltr\.", "Liter", "Liter", flags=re.IGNORECASE, dotted=True),
    NumberedUnit(
        r"Std\.",
        "Stunde",
        "Stunden",
        "f",
        flags=re.IGNORECASE,
        dotted=True,
    ),
    NumberedUnit(
        r"Min\.",
        "Minute",
        "Minuten",
        "f",
        flags=re.IGNORECASE,
        dotted=True,
    ),
    NumberedUnit(
        r"Sek\.",
        "Sekunde",
        "Sekunden",
        "f",
        flags=re.IGNORECASE,
        dotted=True,
    ),
    NumberedUnit(r"Tsd\.", "Tausend", "Tausend", "n", re.IGNORECASE, True),
    NumberedUnit(r"Mio\.", "Million", "Millionen", "f", re.IGNORECASE, True),
    NumberedUnit(r"Mrd\.", "Milliarde", "Milliarden", "f", re.IGNORECASE, True),
    NumberedUnit(r"kg", "Kilogramm", "Kilogramm"),
    NumberedUnit(r"cm", "Zentimeter", "Zentimeter"),
    NumberedUnit(r"mm", "Millimeter", "Millimeter"),
    NumberedUnit(r"km", "Kilometer", "Kilometer"),
    NumberedUnit(r"mg", "Milligramm", "Milligramm"),
    NumberedUnit(r"Hz", "Hertz", "Hertz"),
    NumberedUnit(r"EUR", "Euro", "Euro"),
    NumberedUnit(r"W", "Watt", "Watt"),
    NumberedUnit(r"V", "Volt", "Volt"),
    NumberedUnit(r"g", "Gramm", "Gramm"),
    NumberedUnit(r"m", "Meter", "Meter"),
)


COMPOSITE_ABBREVIATIONS = (
    (re.compile(r"(?<!\w)Lfd\.\s*Nr\.(?!\w)"), "laufende Nummer"),
    (re.compile(r"(?<!\w)z\s*\.\s*b\s*\.?(?!\w)", re.IGNORECASE), "zum Beispiel"),
    (re.compile(r"(?<!\w)zB(?!\w)"), "zum Beispiel"),
    (re.compile(r"(?<!\w)d\s*\.\s*h\s*\.?(?!\w)", re.IGNORECASE), "das heißt"),
    (re.compile(r"(?<!\w)u\s*\.\s*a\s*\.?(?!\w)", re.IGNORECASE), "unter anderem"),
)


MONTH_NAMES = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


MONTHS = {
    "januar": "Januar",
    "jan": "Januar",
    "februar": "Februar",
    "feb": "Februar",
    "märz": "März",
    "mär": "März",
    "maerz": "März",
    "april": "April",
    "apr": "April",
    "mai": "Mai",
    "juni": "Juni",
    "jun": "Juni",
    "juli": "Juli",
    "jul": "Juli",
    "august": "August",
    "aug": "August",
    "september": "September",
    "sep": "September",
    "sept": "September",
    "oktober": "Oktober",
    "okt": "Oktober",
    "november": "November",
    "nov": "November",
    "dezember": "Dezember",
    "dez": "Dezember",
}

LABEL_WORDS = ("Nummer", "laufende Nummer", "Gleis", "Kapitel", "Absatz", "Seite")
