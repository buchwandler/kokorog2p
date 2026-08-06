"""Deprecated compatibility exports for :mod:`abbr2words`.

Abbreviation ownership moved to ``abbr2words``. This module remains importable
for one transition release and intentionally emits no import-time warning.
"""

from abbr2words import (
    AbbreviationContext,
    AbbreviationEntry,
    AbbreviationExpander,
    abbreviation_guards_match,
)

__all__ = [
    "AbbreviationContext",
    "AbbreviationEntry",
    "AbbreviationExpander",
    "abbreviation_guards_match",
]
