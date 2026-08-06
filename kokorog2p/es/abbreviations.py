"""Deprecated Spanish abbreviation compatibility shim.

The registry is owned by :mod:`abbr2words`; this import path remains available
without an import-time warning during the transition release.
"""

from abbr2words.languages.es import (
    SpanishAbbreviationExpander,
    get_expander,
    reset_expander,
)

__all__ = ["SpanishAbbreviationExpander", "get_expander", "reset_expander"]
