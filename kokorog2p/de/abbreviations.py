"""Deprecated German abbreviation compatibility shim backed by Spokenform."""

from spokenform.abbreviations import (
    AbbreviationExpander,
    get_shared_expander,
    reset_expanders,
)

GermanAbbreviationExpander = AbbreviationExpander


def get_expander(enable_context_detection: bool = True) -> AbbreviationExpander:
    return get_shared_expander("de", context=enable_context_detection)


def reset_expander() -> None:
    reset_expanders("de")


__all__ = ["GermanAbbreviationExpander", "get_expander", "reset_expander"]
