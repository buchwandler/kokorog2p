"""Utilities for abbreviation-aware token merging."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol, TypeVar

from abbr2words import (
    AbbreviationEntry,
    abbreviation_guards_match,
    get_shared_expander,
    normalize_language,
)


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


def _get_abbreviation_definitions(lang: str | None) -> list[AbbreviationEntry]:
    """Collect complete abbreviation definitions for a language."""
    normalized = _normalize_lang(lang)

    try:
        # Shared custom registries are keyed by the base language.  Using
        # ``en_US`` here would create/read a different registry from the
        # English compatibility expander's ``en`` registry.
        language = normalize_language(normalized.split("-", 1)[0])
    except ValueError:
        return []
    return list(get_shared_expander(language, context=True).entries.values())


def get_abbreviation_entries(lang: str | None) -> list[tuple[str, bool]]:
    """Collect abbreviation spellings and case behavior for a language.

    Args:
        lang: Language code (e.g., "en-us"). Defaults to English when None.

    Returns:
        List of ``(abbreviation, case_sensitive)`` tuples. Context-guarded
        entries remain part of this inventory; their guards are evaluated by
        :func:`merge_abbreviation_tokens`.
    """
    return [
        (entry.abbreviation, entry.case_sensitive)
        for entry in _get_abbreviation_definitions(lang)
    ]


def _resolve_token_spans(
    tokens: Sequence[TokenT], source_text: str
) -> list[tuple[int, int] | None]:
    """Resolve usable token offsets, including when tracking is disabled."""
    spans: list[tuple[int, int] | None] = []
    cursor = 0

    for token in tokens:
        start = token.char_start
        end = token.char_end
        has_exact_offsets = (
            0 <= start <= end <= len(source_text)
            and source_text[start:end] == token.text
        )
        if has_exact_offsets:
            spans.append((start, end))
            cursor = max(cursor, end)
            continue

        inferred_start = source_text.find(token.text, cursor)
        if inferred_start < 0:
            spans.append(None)
            continue

        inferred_end = inferred_start + len(token.text)
        spans.append((inferred_start, inferred_end))
        cursor = inferred_end

    return spans


def merge_abbreviation_tokens(
    tokens: Sequence[TokenT],
    lang: str | None,
    *,
    is_break: Callable[[TokenT, TokenT, int], bool],
    build_token: Callable[[TokenT, TokenT, str], TokenT],
    source_text: str | None = None,
) -> list[TokenT]:
    """Merge tokens that form known abbreviations.

    Guarded abbreviations are merged only when their original before/after
    context satisfies the same guard used by abbreviation normalization.

    Args:
        tokens: Input tokens.
        lang: Language code for abbreviation lookup.
        is_break: Predicate to stop merging when tokens are non-contiguous.
        build_token: Factory for merged tokens.
        source_text: Complete text from which the tokens were produced. This is
            required to merge context-guarded entries. Unguarded entries remain
            mergeable when it is omitted.

    Returns:
        List of tokens with abbreviation merges applied.
    """
    if len(tokens) < 2:
        return list(tokens)

    definitions = _get_abbreviation_definitions(lang)
    if not definitions:
        return list(tokens)

    case_sensitive = {
        entry.abbreviation: entry for entry in definitions if entry.case_sensitive
    }
    case_insensitive = {
        entry.abbreviation.lower(): entry
        for entry in definitions
        if not entry.case_sensitive
    }
    max_len = max((len(entry.abbreviation) for entry in definitions), default=0)
    if max_len == 0:
        return list(tokens)

    resolved_spans = (
        _resolve_token_spans(tokens, source_text) if source_text is not None else None
    )

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

            entry = case_sensitive.get(combined)
            if entry is None:
                entry = case_insensitive.get(combined.lower())
            if entry is None:
                continue

            is_guarded = bool(entry.only_if_preceded_by or entry.only_if_followed_by)
            if is_guarded:
                if source_text is None or resolved_spans is None:
                    continue
                start_span = resolved_spans[i]
                end_span = resolved_spans[j]
                if start_span is None or end_span is None:
                    continue
                if not abbreviation_guards_match(
                    entry,
                    source_text,
                    start_span[0],
                    end_span[1],
                ):
                    continue

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


__all__ = ["get_abbreviation_entries", "merge_abbreviation_tokens"]
