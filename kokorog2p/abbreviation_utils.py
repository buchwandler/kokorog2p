"""Utilities for abbreviation-aware token merging."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar, cast

from kokorog2p.pipeline.abbreviations import AbbreviationExpander


class AbbreviationToken(Protocol):
    """Protocol for tokens used in abbreviation merging."""

    text: str
    char_start: int
    char_end: int


TokenT = TypeVar("TokenT", bound=AbbreviationToken)


def _normalize_lang(lang: str | None) -> str:
    if not lang:
        return "en-us"
    return lang.lower().replace("_", "-")


def get_abbreviation_entries(lang: str | None) -> list[tuple[str, bool]]:
    """Collect abbreviation entries for a language.

    Args:
        lang: Language code (e.g., "en-us"). Defaults to English when None.

    Returns:
        List of (abbreviation, case_sensitive) tuples.
    """
    normalized = _normalize_lang(lang)
    entries: list[tuple[str, bool]] = []

    module_name: str | None = None
    if normalized.startswith("en"):
        module_name = "kokorog2p.en.abbreviations"
    elif normalized.startswith("de"):
        module_name = "kokorog2p.de.abbreviations"
    elif normalized.startswith("fr"):
        module_name = "kokorog2p.fr.abbreviations"
    elif normalized.startswith("es"):
        module_name = "kokorog2p.es.abbreviations"
    elif normalized.startswith("pt"):
        module_name = "kokorog2p.pt.abbreviations"
    elif normalized.startswith("it"):
        module_name = "kokorog2p.it.abbreviations"
    elif normalized.startswith("cs"):
        module_name = "kokorog2p.cs.abbreviations"
    else:
        return entries

    module = importlib.import_module(module_name)
    get_expander = cast(Callable[[], AbbreviationExpander], module.get_expander)
    expander = get_expander()
    for entry in expander.entries.values():
        entries.append((entry.abbreviation, entry.case_sensitive))

    return entries


def merge_abbreviation_tokens(
    tokens: Sequence[TokenT],
    lang: str | None,
    *,
    is_break: Callable[[TokenT, TokenT, int], bool],
    build_token: Callable[[TokenT, TokenT, str], TokenT],
) -> list[TokenT]:
    """Merge tokens that form known abbreviations.

    Args:
        tokens: Input tokens.
        lang: Language code for abbreviation lookup.
        is_break: Predicate to stop merging when tokens are non-contiguous.
        build_token: Factory for merged tokens.

    Returns:
        List of tokens with abbreviation merges applied.
    """
    if len(tokens) < 2:
        return list(tokens)

    entries = get_abbreviation_entries(lang)
    if not entries:
        return list(tokens)

    case_sensitive = {
        abbrev for abbrev, is_case_sensitive in entries if is_case_sensitive
    }
    case_insensitive = {
        abbrev.lower() for abbrev, is_case_sensitive in entries if not is_case_sensitive
    }
    max_len = max((len(abbrev) for abbrev, _ in entries), default=0)
    if max_len == 0:
        return list(tokens)

    merged: list[TokenT] = []
    i = 0
    while i < len(tokens):
        best_end: int | None = None
        best_text: str | None = None
        combined = ""
        last_end = tokens[i].char_end

        for j in range(i, len(tokens)):
            if j > i and is_break(tokens[j - 1], tokens[j], last_end):
                break
            combined += tokens[j].text
            last_end = tokens[j].char_end
            if len(combined) > max_len:
                break

            if combined in case_sensitive or combined.lower() in case_insensitive:
                best_end = j
                best_text = combined

        if best_end is not None and best_end > i:
            merged.append(
                build_token(tokens[i], tokens[best_end], best_text or combined)
            )
            i = best_end + 1
            continue

        merged.append(tokens[i])
        i += 1

    return merged


__all__ = ["merge_abbreviation_tokens", "get_abbreviation_entries"]
