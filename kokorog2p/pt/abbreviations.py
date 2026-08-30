"""Deprecated Portuguese abbreviation compatibility shim backed by Spokenform."""

from spokenform.abbreviations import (
    AbbreviationExpander,
    get_shared_expander,
    reset_expanders,
)

PortugueseAbbreviationExpander = AbbreviationExpander


def get_expander(enable_context_detection: bool = True) -> AbbreviationExpander:
    return get_shared_expander("pt", context=enable_context_detection)


def reset_expander() -> None:
    reset_expanders("pt")


__all__ = ["PortugueseAbbreviationExpander", "get_expander", "reset_expander"]
