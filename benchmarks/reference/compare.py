"""Pure comparison engine for candidate/reference results."""

from __future__ import annotations

import difflib
import unicodedata
from collections.abc import Iterable, Sequence
from typing import TypeVar

from .candidate import analyze_model_encoding
from .types import (
    CandidateOutput,
    CaseComparison,
    ComparisonSummary,
    CorpusCase,
    ReferenceOutput,
    SymbolDiff,
)

T = TypeVar("T")


def _index_unique(values: Sequence[T], label: str) -> dict[str, T]:
    result: dict[str, T] = {}
    for value in values:
        case_id = getattr(value, "case_id", getattr(value, "id", None))
        if not case_id:
            raise ValueError(f"{label} result has no case ID")
        if case_id in result:
            raise ValueError(f"duplicate {label} case ID: {case_id}")
        result[case_id] = value
    return result


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).split())


def _symbols(value: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFC", value) if not ch.isspace())


def _symbol_diff(left: str, right: str) -> SymbolDiff:
    matcher = difflib.SequenceMatcher(a=left, b=right, autojunk=False)
    insertions = deletions = substitutions = 0
    first_difference: int | None = None
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if first_difference is None:
            first_difference = i1
        if tag == "insert":
            insertions += j2 - j1
        elif tag == "delete":
            deletions += i2 - i1
        else:
            substitutions += max(i2 - i1, j2 - j1)
    return SymbolDiff(
        insertions=insertions,
        deletions=deletions,
        substitutions=substitutions,
        first_difference=first_difference,
        edit_distance=insertions + deletions + substitutions,
    )


def _classification(
    candidate: CandidateOutput,
    reference: ReferenceOutput,
    exact: bool,
    normalized: bool,
    encoding: object | None = None,
) -> str:
    if not candidate.ok:
        return "candidate-error"
    if not reference.ok:
        return "reference-error"
    if encoding is not None and getattr(encoding, "encoding_loss", False):
        return "candidate-encoding-loss"
    if exact:
        return "exact"
    if normalized:
        return "whitespace-only"
    if candidate.phonemes.translate(
        str.maketrans("", "", "!?.,;:'\"")
    ) == reference.phonemes.translate(str.maketrans("", "", "!?.,;:'\"")):
        return "punctuation"
    if candidate.phonemes.replace("ˈ", "").replace(
        "ˌ", ""
    ) == reference.phonemes.replace("ˈ", "").replace("ˌ", ""):
        return "stress"
    return "pronunciation"


def compare_results(
    cases: Iterable[CorpusCase],
    candidate_results: Sequence[CandidateOutput],
    reference_results: Sequence[ReferenceOutput],
    *,
    model: str = "1.0",
    sample_limit: int = 100,
) -> ComparisonSummary:
    """Compare result collections by stable case ID, never by list position."""
    case_values = tuple(cases)
    case_index = _index_unique(case_values, "corpus")
    candidate_index = _index_unique(candidate_results, "candidate")
    reference_index = _index_unique(reference_results, "reference")
    expected = set(case_index)
    if set(candidate_index) != expected:
        missing = sorted(expected - set(candidate_index))
        extra = sorted(set(candidate_index) - expected)
        raise ValueError(
            f"candidate case IDs do not match corpus: missing={missing}, extra={extra}"
        )
    if set(reference_index) != expected:
        missing = sorted(expected - set(reference_index))
        extra = sorted(set(reference_index) - expected)
        raise ValueError(
            f"reference case IDs do not match corpus: missing={missing}, extra={extra}"
        )

    comparisons: list[CaseComparison] = []
    exact_count = normalized_count = symbol_count = id_count = 0
    candidate_success = reference_success = comparable = 0
    candidate_encoding_failures = reference_encoding_failures = 0
    candidate_encoding_loss = reference_encoding_loss = 0

    for case in case_values:
        candidate = candidate_index[case.id]
        reference = reference_index[case.id]
        if candidate.ok:
            candidate_success += 1
        if reference.ok:
            reference_success += 1
        candidate_encoding = (
            candidate.encoding
            if candidate.encoding is not None
            else analyze_model_encoding(candidate.phonemes, model=model)
            if candidate.ok
            else None
        )
        if candidate_encoding is not None and not candidate_encoding.valid:
            candidate_encoding_failures += 1
        if candidate_encoding is not None and candidate_encoding.encoding_loss:
            candidate_encoding_loss += 1
        reference_encoding = (
            analyze_model_encoding(reference.phonemes, model=model)
            if reference.ok
            else None
        )
        if reference_encoding is not None and not reference_encoding.valid:
            reference_encoding_failures += 1
        if reference_encoding is not None and reference_encoding.encoding_loss:
            reference_encoding_loss += 1
        if reference_encoding is not None and reference.ok:
            reference = ReferenceOutput(
                case_id=reference.case_id,
                input_text=reference.input_text,
                normalized_text=reference.normalized_text,
                phonemes=reference.phonemes,
                error=reference.error,
            )
        both_ok = candidate.ok and reference.ok
        if both_ok:
            comparable += 1
        exact = both_ok and candidate.phonemes == reference.phonemes
        normalized = both_ok and _normalized(candidate.phonemes) == _normalized(
            reference.phonemes
        )
        candidate_symbols = _symbols(candidate.phonemes)
        reference_symbols = _symbols(reference.phonemes)
        symbol_match = both_ok and candidate_symbols == reference_symbols
        model_id_match: bool | None = None
        if (
            both_ok
            and candidate_encoding is not None
            and not candidate_encoding.encoding_loss
            and reference_encoding is not None
            and not reference_encoding.encoding_loss
        ):
            model_id_match = (
                candidate_encoding.token_ids == reference_encoding.token_ids
            )
        if exact:
            exact_count += 1
        if normalized:
            normalized_count += 1
        if symbol_match:
            symbol_count += 1
        if model_id_match:
            id_count += 1
        comparison = CaseComparison(
            case_id=case.id,
            input_text=case.text,
            candidate_ok=candidate.ok,
            reference_ok=reference.ok,
            exact_phoneme_match=exact,
            normalized_phoneme_match=normalized,
            model_symbol_match=symbol_match,
            model_id_match=model_id_match,
            symbol_diff=_symbol_diff(candidate_symbols, reference_symbols),
            classification=_classification(
                candidate, reference, exact, normalized, candidate_encoding
            ),
            candidate=candidate,
            reference=reference,
        )
        comparisons.append(comparison)

    differences = [
        comparison for comparison in comparisons if not comparison.exact_phoneme_match
    ]
    return ComparisonSummary(
        cases=tuple(comparisons),
        difference_count=len(differences),
        difference_samples=tuple(differences[:sample_limit]),
        cases_total=len(comparisons),
        candidate_success=candidate_success,
        reference_success=reference_success,
        comparable_cases=comparable,
        exact_phoneme_matches=exact_count,
        normalized_phoneme_matches=normalized_count,
        model_symbol_matches=symbol_count,
        model_id_matches=id_count,
        candidate_encoding_failures=candidate_encoding_failures,
        reference_encoding_failures=reference_encoding_failures,
        candidate_encoding_loss=candidate_encoding_loss,
        reference_encoding_loss=reference_encoding_loss,
    )


compare_case_results = compare_results
