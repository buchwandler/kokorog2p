"""Unicode-aware lexical subtokenization for English frontend realization."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass


@dataclass(slots=True)
class EnglishSubtoken:
    """One lexical part of a whitespace-free English source token."""

    text: str
    start: int
    end: int
    phonemes: str | None = None
    source: str | None = None

    @property
    def is_letter_name(self) -> bool:
        return len(self.text) == 1 and self.text.isalpha()


def _is_word_character(char: str) -> bool:
    return char.isalnum() or unicodedata.category(char).startswith("L")


def split_english_lexical_token(text: str) -> tuple[EnglishSubtoken, ...]:
    """Split one token at Unicode, case, digit, and punctuation boundaries."""
    result: list[EnglishSubtoken] = []
    start: int | None = None

    def flush(end: int) -> None:
        nonlocal start
        if start is not None and start < end:
            result.append(EnglishSubtoken(text[start:end], start, end))
        start = None

    for index, char in enumerate(text):
        if not _is_word_character(char):
            flush(index)
            continue
        if start is None:
            start = index
            continue
        previous = text[index - 1]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if (
            char.isdigit() != previous.isdigit()
            or (previous.islower() and char.isupper())
            or (previous.isupper() and char.isupper() and next_char.islower())
        ):
            flush(index)
            start = index
    flush(len(text))
    return tuple(result)


__all__ = ["EnglishSubtoken", "split_english_lexical_token"]
