"""Pairwise source overlap and pronunciation agreement."""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from itertools import combinations

from .kokoro_view import to_kokoro_view
from .model import ParsedLexicon


def _keyed_words(lexicon: ParsedLexicon, key: str) -> dict[str, tuple[str, ...]]:
    transform = {
        "exact": lambda x: x,
        "lower": str.lower,
        "casefold": str.casefold,
        "nfc": lambda x: unicodedata.normalize("NFC", x),
    }[key]
    result: dict[str, list[str]] = {}
    for word in lexicon.words:
        result.setdefault(transform(word), []).append(word)
    return {key: tuple(values) for key, values in result.items()}


def pair_metrics(left: ParsedLexicon, right: ParsedLexicon) -> dict[str, object]:
    exact = set(left.words) & set(right.words)
    lower = set(_keyed_words(left, "lower")) & set(_keyed_words(right, "lower"))
    casefold = set(_keyed_words(left, "casefold")) & set(
        _keyed_words(right, "casefold")
    )
    raw_agreement = 0
    any_agreement = 0
    nfc_agreement = 0
    kokoro_agreement = 0
    conflicts: list[dict[str, object]] = []
    for word in sorted(exact):
        left_values = left.lookup_all(word)
        right_values = right.lookup_all(word)
        left_set = set(left_values)
        right_set = set(right_values)
        raw = left_values == right_values
        any_match = bool(left_set & right_set)
        left_nfc = {unicodedata.normalize("NFC", value) for value in left_values}
        right_nfc = {unicodedata.normalize("NFC", value) for value in right_values}
        nfc_match = bool(left_nfc & right_nfc)
        left_view = {
            to_kokoro_view(left.source.source_id, value) for value in left_values
        }
        right_view = {
            to_kokoro_view(right.source.source_id, value) for value in right_values
        }
        kokoro = bool(left_view & right_view)
        raw_agreement += raw
        any_agreement += any_match
        nfc_agreement += nfc_match
        kokoro_agreement += kokoro
        if not raw or not any_match:
            conflicts.append(
                {
                    "word": word,
                    "source_a": left_values,
                    "source_b": right_values,
                    "raw_exact": raw,
                    "nfc_match": nfc_match,
                    "kokoro_match": kokoro,
                }
            )
    union = len(set(left.words) | set(right.words))
    return {
        "source_a": left.source.source_id,
        "source_b": right.source.source_id,
        "unique_words_a": len(left.entries),
        "unique_words_b": len(right.entries),
        "exact_spelling_intersection": len(exact),
        "lowercase_spelling_intersection": len(lower),
        "casefold_spelling_intersection": len(casefold),
        "jaccard_word_overlap": len(exact) / union if union else 0.0,
        "exact_raw_pronunciation_agreement": raw_agreement,
        "any_variant_raw_agreement": any_agreement,
        "nfc_only_agreement": nfc_agreement,
        "kokoro_view_any_variant_agreement": kokoro_agreement,
        "conflicting_overlapping_words": len(conflicts),
        "conflicts": conflicts,
    }


def all_pair_metrics(lexica: Mapping[str, ParsedLexicon]) -> list[dict[str, object]]:
    return [
        pair_metrics(lexica[left], lexica[right])
        for left, right in combinations(sorted(lexica), 2)
    ]
