"""Exact, casing, and Unicode collision analysis."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable, Mapping

from .model import ParsedLexicon


def collision_groups(
    words: Iterable[str], key: Callable[[str], str]
) -> dict[str, tuple[str, ...]]:
    groups: dict[str, list[str]] = {}
    for word in words:
        groups.setdefault(key(word), []).append(word)
    return {value: tuple(items) for value, items in groups.items() if len(items) > 1}


def casing_collisions(lexicon: ParsedLexicon) -> dict[str, dict[str, tuple[str, ...]]]:
    words = lexicon.words
    return {
        "exact": collision_groups(words, lambda value: value),
        "lower": collision_groups(words, str.lower),
        "casefold": collision_groups(words, str.casefold),
    }


def unicode_statistics(lexicon: ParsedLexicon) -> dict[str, object]:
    records = list(lexicon.iter_records())
    nfc_words = {unicodedata.normalize("NFC", word) for word in lexicon.words}
    nfd_words = {unicodedata.normalize("NFD", word) for word in lexicon.words}
    return {
        "nfc_rows": sum(
            unicodedata.normalize("NFC", word) == word for word, _ in records
        ),
        "non_nfc_rows": sum(
            unicodedata.normalize("NFC", word) != word for word, _ in records
        ),
        "nfc_ipa_rows": sum(
            unicodedata.normalize("NFC", record.ipa) == record.ipa
            for _, record in records
        ),
        "non_nfc_ipa_rows": sum(
            unicodedata.normalize("NFC", record.ipa) != record.ipa
            for _, record in records
        ),
        "nfd_equivalent_word_groups": len(
            collision_groups(
                lexicon.words, lambda value: unicodedata.normalize("NFD", value)
            )
        ),
        "nfc_distinct_words": len(nfc_words),
        "nfd_distinct_words": len(nfd_words),
        "nfc_word_collisions": collision_groups(
            lexicon.words, lambda value: unicodedata.normalize("NFC", value)
        ),
    }


def key_report(lexica: Mapping[str, ParsedLexicon]) -> dict[str, object]:
    return {
        source: {
            "collisions": casing_collisions(lexicon),
            "unicode": unicode_statistics(lexicon),
        }
        for source, lexicon in lexica.items()
    }
