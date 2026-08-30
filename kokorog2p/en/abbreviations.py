"""Deprecated English abbreviation compatibility shim."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace
from typing import cast

from spokenform.abbreviations import (
    ExpansionResult,
    ProtectedSpan,
    TokenAnnotation,
    get_expander_class,
    get_shared_expander,
    reset_expanders,
)

_EnglishAbbreviationExpander = get_expander_class("en")


class EnglishAbbreviationExpander(_EnglishAbbreviationExpander):
    """English abbreviation compatibility adapter.

    ``abbr2words`` owns the registry and matching rules.  This small adapter
    retains kokorog2p's historical direct-expander output for callers that
    still use this compatibility class directly.
    """

    def __init__(self, enable_context_detection: bool = True) -> None:
        super().__init__(enable_context_detection=enable_context_detection)
        self._apply_legacy_defaults()

    def _apply_legacy_defaults(self) -> None:
        """Restore direct-expander defaults retained by kokorog2p."""
        entry = self.get_abbreviation("Mrs.")
        if entry is not None and entry.expansion == "Missus":
            self.add_abbreviation(replace(entry, expansion="Misses"))

    def expand(
        self,
        text: str,
        *,
        annotations: Iterable[TokenAnnotation] | None = None,
        protected_spans: Iterable[
            ProtectedSpan | tuple[int, int] | tuple[int, int, str | None]
        ]
        | None = None,
    ) -> str:
        result: ExpansionResult = self.expand_with_replacements(
            text, annotations=annotations, protected_spans=protected_spans
        )
        if result.replacements:
            last = result.replacements[-1]
            stripped_result = result.text.rstrip()
            if (
                last.end == len(text.rstrip())
                and text.rstrip().endswith(".")
                and last.text.endswith(".")
            ):
                return stripped_result[:-1] + result.text[len(stripped_result) :]
        return result.text


def get_expander(
    enable_context_detection: bool = True,
) -> EnglishAbbreviationExpander:
    """Return the shared English registry for the requested context mode."""
    expander = get_shared_expander("en", context=enable_context_detection)
    if not isinstance(expander, EnglishAbbreviationExpander):
        # abbr2words may have initialized the public shared registry before
        # this compatibility module was imported.  Preserve that registry's
        # identity while attaching the legacy adapter to the existing object.
        expander.__class__ = EnglishAbbreviationExpander
        cast(EnglishAbbreviationExpander, expander)._apply_legacy_defaults()
    return cast(EnglishAbbreviationExpander, expander)


def reset_expander() -> None:
    """Reset all shared English registries."""
    reset_expanders("en")


__all__ = ["EnglishAbbreviationExpander", "get_expander", "reset_expander"]
