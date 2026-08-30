"""Deprecated Spanish abbreviation compatibility shim backed by Spokenform."""

from spokenform.abbreviations import (
    AbbreviationExpander,
    get_shared_expander,
    reset_expanders,
)

SpanishAbbreviationExpander = AbbreviationExpander


def get_expander(enable_context_detection: bool = True) -> AbbreviationExpander:
    return get_shared_expander("es", context=enable_context_detection)


def reset_expander() -> None:
    reset_expanders("es")


__all__ = ["SpanishAbbreviationExpander", "get_expander", "reset_expander"]
