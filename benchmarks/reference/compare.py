"""Pure comparison engine for candidate/reference results."""

from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import replace
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


def _without_punctuation(value: str) -> str:
    return "".join(
        ch
        for ch in unicodedata.normalize("NFC", value)
        if not unicodedata.category(ch).startswith("P")
    )


def _without_stress(value: str) -> str:
    return value.replace("ˈ", "").replace("ˌ", "")


def _symbol_diff(left: str, right: str) -> SymbolDiff:
    """Return true Levenshtein operation counts for two short symbol strings."""
    rows = len(left) + 1
    columns = len(right) + 1
    distances = [[0] * columns for _ in range(rows)]
    operations: list[list[tuple[int, int, int]]] = [
        [(0, 0, 0) for _ in range(columns)] for _ in range(rows)
    ]
    for i in range(rows):
        distances[i][0] = i
        if i:
            operations[i][0] = (0, i, 0)
    for j in range(columns):
        distances[0][j] = j
        if j:
            operations[0][j] = (j, 0, 0)

    for i in range(1, rows):
        for j in range(1, columns):
            if left[i - 1] == right[j - 1]:
                distances[i][j] = distances[i - 1][j - 1]
                operations[i][j] = operations[i - 1][j - 1]
                continue
            candidates = [
                (
                    distances[i - 1][j] + 1,
                    (
                        operations[i - 1][j][0],
                        operations[i - 1][j][1] + 1,
                        operations[i - 1][j][2],
                    ),
                ),
                (
                    distances[i][j - 1] + 1,
                    (
                        operations[i][j - 1][0] + 1,
                        operations[i][j - 1][1],
                        operations[i][j - 1][2],
                    ),
                ),
                (
                    distances[i - 1][j - 1] + 1,
                    (
                        operations[i - 1][j - 1][0],
                        operations[i - 1][j - 1][1],
                        operations[i - 1][j - 1][2] + 1,
                    ),
                ),
            ]
            distances[i][j], operations[i][j] = min(
                candidates, key=lambda item: item[0]
            )

    first_difference: int | None = None
    for index, (left_char, right_char) in enumerate(zip(left, right)):
        if left_char != right_char:
            first_difference = index
            break
    if first_difference is None and len(left) != len(right):
        first_difference = min(len(left), len(right))
    insertions, deletions, substitutions = operations[-1][-1]
    return SymbolDiff(
        insertions=insertions,
        deletions=deletions,
        substitutions=substitutions,
        first_difference=first_difference,
        edit_distance=distances[-1][-1],
    )


def _classification(
    candidate: CandidateOutput,
    reference: ReferenceOutput,
    exact: bool,
    normalized: bool,
    candidate_encoding: object | None,
    api_ids_consistent: bool | None,
    reference_encoding: object | None,
) -> str:
    if not candidate.ok:
        return "candidate-error"
    if not reference.ok:
        return "reference-error"
    if api_ids_consistent is False:
        return "candidate-api-id-mismatch"
    if candidate_encoding is not None and getattr(
        candidate_encoding, "encoding_loss", False
    ):
        return "candidate-encoding-loss"
    if reference_encoding is not None and getattr(
        reference_encoding, "encoding_loss", False
    ):
        return "reference-encoding-loss"
    if exact:
        return "exact"
    if normalized:
        return "whitespace-only"
    if _without_punctuation(candidate.phonemes) == _without_punctuation(
        reference.phonemes
    ):
        return "punctuation"
    if _without_stress(candidate.phonemes) == _without_stress(reference.phonemes):
        return "stress"
    return "pronunciation"


def _evaluate_policy(
    policy: str,
    *,
    candidate_ok: bool,
    reference_ok: bool,
    exact: bool,
    normalized: bool,
    model_id_match: bool | None,
    candidate_encoding: object | None,
) -> bool | None:
    if policy == "diagnostic":
        return None
    if not candidate_ok or not reference_ok:
        return False
    if policy == "exact":
        return exact
    if policy == "normalized":
        return normalized
    if policy == "model-id":
        return model_id_match is True
    if policy == "model-valid":
        return bool(
            candidate_encoding is not None
            and getattr(candidate_encoding, "valid", False)
            and not getattr(candidate_encoding, "encoding_loss", True)
        )
    raise ValueError(f"unsupported case policy: {policy}")


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
    model_id_comparable = 0
    policy_passed = policy_failed = 0
    diagnostic_cases = diagnostic_differences = 0
    candidate_errors = reference_errors = api_mismatches = 0
    policy_counts: Counter[str] = Counter()
    policy_failure_counts: Counter[str] = Counter()
    classification_counts: Counter[str] = Counter()

    for case in case_values:
        candidate = candidate_index[case.id]
        reference = reference_index[case.id]
        candidate_success += int(candidate.ok)
        reference_success += int(reference.ok)
        candidate_errors += int(not candidate.ok)
        reference_errors += int(not reference.ok)
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
            reference.encoding
            if reference.encoding is not None
            else analyze_model_encoding(reference.phonemes, model=model)
            if reference.ok
            else None
        )
        if reference_encoding is not None and not reference_encoding.valid:
            reference_encoding_failures += 1
        if reference_encoding is not None and reference_encoding.encoding_loss:
            reference_encoding_loss += 1
        if reference.encoding is None and reference_encoding is not None:
            reference = replace(reference, encoding=reference_encoding)

        both_ok = candidate.ok and reference.ok
        comparable += int(both_ok)
        exact = both_ok and candidate.phonemes == reference.phonemes
        normalized = both_ok and _normalized(candidate.phonemes) == _normalized(
            reference.phonemes
        )
        candidate_symbols = _symbols(candidate.phonemes)
        reference_symbols = _symbols(reference.phonemes)
        symbol_match = both_ok and candidate_symbols == reference_symbols
        api_ids_consistent = (
            candidate.token_ids == candidate_encoding.token_ids
            if candidate.ok and candidate_encoding is not None
            else None
        )
        api_mismatches += int(api_ids_consistent is False)
        model_id_match: bool | None = None
        if (
            both_ok
            and api_ids_consistent is True
            and candidate_encoding is not None
            and not candidate_encoding.encoding_loss
            and reference_encoding is not None
            and not reference_encoding.encoding_loss
        ):
            model_id_comparable += 1
            model_id_match = candidate.token_ids == reference_encoding.token_ids
        exact_count += int(exact)
        normalized_count += int(normalized)
        symbol_count += int(symbol_match)
        id_count += int(model_id_match is True)
        policy_result = _evaluate_policy(
            case.policy,
            candidate_ok=candidate.ok,
            reference_ok=reference.ok,
            exact=exact,
            normalized=normalized,
            model_id_match=model_id_match,
            candidate_encoding=candidate_encoding,
        )
        policy_counts[case.policy] += 1
        if policy_result is True:
            policy_passed += 1
        elif policy_result is False:
            policy_failed += 1
            policy_failure_counts[case.policy] += 1
        diagnostic_cases += int(case.policy == "diagnostic")
        comparison = CaseComparison(
            case_id=case.id,
            input_text=case.text,
            policy=case.policy,
            policy_passed=policy_result,
            candidate_ok=candidate.ok,
            reference_ok=reference.ok,
            exact_phoneme_match=exact,
            normalized_phoneme_match=normalized,
            model_symbol_match=symbol_match,
            model_id_match=model_id_match,
            symbol_diff=_symbol_diff(candidate_symbols, reference_symbols),
            classification=_classification(
                candidate,
                reference,
                exact,
                normalized,
                candidate_encoding,
                api_ids_consistent,
                reference_encoding,
            ),
            candidate=candidate,
            reference=reference,
            candidate_api_ids_consistent=api_ids_consistent,
        )
        classification_counts[comparison.classification] += 1
        diagnostic_differences += int(case.policy == "diagnostic" and not exact)
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
        policy_cases=len(comparisons) - diagnostic_cases,
        policy_passed=policy_passed,
        policy_failed=policy_failed,
        diagnostic_cases=diagnostic_cases,
        diagnostic_differences=diagnostic_differences,
        candidate_errors=candidate_errors,
        reference_errors=reference_errors,
        candidate_api_id_mismatches=api_mismatches,
        model_id_comparable_cases=model_id_comparable,
        classification_counts=dict(classification_counts),
        policy_counts=dict(policy_counts),
        policy_failure_counts=dict(policy_failure_counts),
    )


compare_case_results = compare_results
