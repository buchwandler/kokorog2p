"""Deprecated Italian abbreviation compatibility shim backed by Spokenform."""

from spokenform.abbreviations import (
    AbbreviationExpander,
    get_shared_expander,
    reset_expanders,
)

ItalianAbbreviationExpander = AbbreviationExpander


def get_expander(enable_context_detection: bool = True) -> AbbreviationExpander:
    return get_shared_expander("it", context=enable_context_detection)


def reset_expander() -> None:
    reset_expanders("it")


__all__ = ["ItalianAbbreviationExpander", "get_expander", "reset_expander"]
