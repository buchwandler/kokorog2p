"""Deprecated English abbreviation compatibility shim."""

from __future__ import annotations

from abbr2words import get_shared_expander, reset_expanders
from abbr2words.languages.en import EnglishAbbreviationExpander


def get_expander(
    enable_context_detection: bool = True,
) -> EnglishAbbreviationExpander:
    """Return the shared English registry for the requested context mode."""
    return get_shared_expander("en", context=enable_context_detection)


def reset_expander() -> None:
    """Reset all shared English registries."""
    reset_expanders("en")


__all__ = ["EnglishAbbreviationExpander", "get_expander", "reset_expander"]
