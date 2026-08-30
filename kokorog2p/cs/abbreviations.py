"""Deprecated Czech abbreviation compatibility shim backed by Spokenform."""

from spokenform.abbreviations import (
    AbbreviationExpander,
    get_shared_expander,
    reset_expanders,
)

CzechAbbreviationExpander = AbbreviationExpander


def get_expander(enable_context_detection: bool = True) -> AbbreviationExpander:
    return get_shared_expander("cs", context=enable_context_detection)


def reset_expander() -> None:
    reset_expanders("cs")


__all__ = ["CzechAbbreviationExpander", "get_expander", "reset_expander"]
