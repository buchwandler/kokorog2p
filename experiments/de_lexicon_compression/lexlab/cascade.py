"""Ordered multi-source cascade and analysis-only sharing metrics."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence

from .metrics import cer


def _source_id(source) -> str:
    info = source.source
    return info.source_id


def lookup_cascade(sources: Sequence, word: str) -> dict[str, object]:
    candidates = []
    hits_by_source: Counter[str] = Counter()
    for source in sources:
        values = tuple(source.lookup_all(word))
        source_id = _source_id(source)
        if values:
            hits_by_source[source_id] += 1
        candidates.append((source_id, values))
    selected_source = None
    selected = ()
    for source_id, values in candidates:
        if values:
            selected_source = source_id
            selected = values
            break
    nonempty = [values for _source, values in candidates if values]
    conflict = len({values for values in nonempty}) > 1
    return {
        "word": word,
        "selected_source": selected_source,
        "selected": selected,
        "candidates": {source_id: values for source_id, values in candidates},
        "hit_sources": [source_id for source_id, values in candidates if values],
        "conflict": conflict,
        "hits_by_source": dict(hits_by_source),
    }


def score_cascade(
    sources: Sequence,
    examples: Iterable[tuple[str, tuple[str, ...]]],
) -> dict[str, object]:
    rows = []
    expected_values = []
    selected_values = []
    hits_by_source: Counter[str] = Counter()
    incremental_hits_by_source: Counter[str] = Counter()
    incremental_exact_matches_by_source: Counter[str] = Counter()
    incremental_errors_by_source: Counter[str] = Counter()
    conflict_wins_by_source: Counter[str] = Counter()
    fallback_rows = 0
    selected_exact = 0
    oracle_exact = 0
    for word, expected in examples:
        result = lookup_cascade(sources, word)
        selected = result["selected"]
        selected_source = result["selected_source"]
        expected_values.append(expected)
        selected_values.append(selected)
        for source_id in result["hit_sources"]:
            hits_by_source[source_id] += 1
        if selected_source is None:
            fallback_rows += 1
        else:
            incremental_hits_by_source[selected_source] += 1
            if selected == expected:
                incremental_exact_matches_by_source[selected_source] += 1
            else:
                incremental_errors_by_source[selected_source] += 1
        if result["conflict"] and selected_source is not None:
            conflict_wins_by_source[selected_source] += 1
        selected_match = selected == expected
        oracle_match = expected in {
            value for values in result["candidates"].values() for value in values
        }
        selected_exact += selected_match
        oracle_exact += oracle_match
        rows.append(
            {
                "word": word,
                "selected_source": selected_source,
                "selected_exact": selected_match,
                "oracle_exact": oracle_match,
                "conflict": result["conflict"],
                "hit_sources": "|".join(result["hit_sources"]),
            }
        )
    total = len(rows)
    return {
        "sources": [_source_id(source) for source in sources],
        "entries": total,
        "coverage": (total - fallback_rows) / total if total else 0.0,
        "selected_exact_match_rate": selected_exact / total if total else 0.0,
        "oracle_variant_exact_match_rate": oracle_exact / total if total else 0.0,
        "selected_cer": cer(tuple(expected_values), tuple(selected_values)),
        "fallback_rows": fallback_rows,
        "hits_by_source": dict(hits_by_source),
        "incremental_hits_by_source": dict(incremental_hits_by_source),
        "incremental_exact_matches_by_source": dict(
            incremental_exact_matches_by_source
        ),
        "incremental_errors_by_source": dict(incremental_errors_by_source),
        "conflict_wins_by_source": dict(conflict_wins_by_source),
        "rows": rows,
    }


def cross_source_sharing(sources: Sequence) -> dict[str, object]:
    """Calculate theoretical sharing only; never emit a merged asset."""
    pair_rows = []
    identical_spelling_ipa = 0
    identical_spelling_variant = 0
    shared_ipa_strings = 0
    shared_atom_tuples = 0
    shared_derived = 0
    for index, left in enumerate(sources):
        for right in sources[index + 1 :]:
            common = set(left.words) & set(right.words)
            exact = sum(
                left.lookup_all(word) == right.lookup_all(word) for word in common
            )
            any_variant = sum(
                bool(set(left.lookup_all(word)) & set(right.lookup_all(word)))
                for word in common
            )
            left_ipa = {value for word in left.words for value in left.lookup_all(word)}
            right_ipa = {
                value
                for word in right.words
                for value in right.lookup_all(word)
            }
            ipa_overlap = len(left_ipa & right_ipa)
            shared_atoms = sum(
                left.lookup_all(word) == right.lookup_all(word) for word in common
            )
            left_derived = getattr(left, "derived", {})
            right_derived = getattr(right, "derived", {})
            derived_overlap = len(set(left_derived) & set(right_derived))
            identical_spelling_ipa += exact
            identical_spelling_variant += any_variant
            shared_ipa_strings += ipa_overlap
            shared_atom_tuples += shared_atoms
            shared_derived += derived_overlap
            pair_rows.append(
                {
                    "source_a": _source_id(left),
                    "source_b": _source_id(right),
                    "identical_spelling_identical_raw_ipa": exact,
                    "identical_spelling_shared_variant": any_variant,
                    "identical_ipa_strings": ipa_overlap,
                    "shared_atom_spelling_ipa_tuples": shared_atoms,
                    "shared_derived_decompositions": derived_overlap,
                }
            )
    return {
        "identical_spelling_identical_raw_ipa": identical_spelling_ipa,
        "identical_spelling_shared_variant": identical_spelling_variant,
        "identical_ipa_strings_across_words": shared_ipa_strings,
        "shared_atom_spelling_ipa_tuples": shared_atom_tuples,
        "shared_derived_decompositions": shared_derived,
        "theoretical_savings": {
            "shared_ipa_pool": shared_ipa_strings,
            "shared_word_key_pool": identical_spelling_ipa,
            "shared_atom_pool": shared_atom_tuples,
        },
        "pairs": pair_rows,
    }
