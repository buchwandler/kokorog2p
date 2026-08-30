"""Deprecated French abbreviation compatibility shim backed by Spokenform."""

from spokenform.abbreviations import (
    AbbreviationExpander,
    get_shared_expander,
    reset_expanders,
)

FrenchAbbreviationExpander = AbbreviationExpander


def get_expander(enable_context_detection: bool = True) -> AbbreviationExpander:
    return get_shared_expander("fr", context=enable_context_detection)


def reset_expander() -> None:
    reset_expanders("fr")


__all__ = ["FrenchAbbreviationExpander", "get_expander", "reset_expander"]
