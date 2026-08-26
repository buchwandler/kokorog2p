#!/usr/bin/env python3
"""Benchmark the Swedish clean-room rules against an explicitly supplied TSV.

This module is deliberately independent of runtime package data.  The TSV is
read as a stream and is never imported by ``kokorog2p``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

from kokorog2p.sv.rules import SwedishRuleResult, phonemize_word_raw

EXPECTED_SHA256 = "65eb3aae9c737f6d04c22a44b2ab836d1ec01f682b1cdee07bb2209852355296"
FAILURE_HEADER = (
    "line",
    "word",
    "expected",
    "actual",
    "exact",
    "stressless_equal",
    "quantityless_equal",
    "edit_distance",
    "reference_phone_count",
    "actual_phone_count",
    "feature_tags",
    "rule_ids",
)


@dataclass(frozen=True)
class ReferenceCase:
    line_number: int
    word: str
    phones: tuple[str, ...]

    @property
    def expected(self) -> tuple[str, ...]:
        return self.phones


@dataclass(frozen=True)
class CaseComparison:
    case: ReferenceCase
    actual: tuple[str, ...]
    result: SwedishRuleResult
    exact: bool
    stressless_equal: bool
    quantityless_equal: bool
    edit_distance: int
    substitutions: int
    insertions: int
    deletions: int


def iter_reference_cases(path: Path) -> Iterator[ReferenceCase]:
    """Stream ``word<TAB>space-separated IPA`` rows from *path*."""
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, raw in enumerate(handle, 1):
            raw = raw.rstrip("\r\n")
            if not raw:
                continue
            try:
                word, ipa = raw.split("\t", 1)
            except ValueError as exc:
                raise ValueError(
                    f"{path}:{line_number}: expected word<TAB>ipa"
                ) from exc
            phones = tuple(phone for phone in ipa.split(" ") if phone)
            if not word or not phones:
                raise ValueError(f"{path}:{line_number}: empty word or pronunciation")
            yield ReferenceCase(line_number, word, phones)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stable_split(word: str) -> str:
    bucket = (
        int.from_bytes(hashlib.sha256(word.encode("utf-8")).digest()[:4], "big") % 100
    )
    if bucket < 80:
        return "train"
    if bucket < 90:
        return "dev"
    return "test"


def split_for_word(word: str) -> str:
    """Public alias for the deterministic train/dev/test assignment."""
    return stable_split(word)


def without_stress(phones: Sequence[str]) -> tuple[str, ...]:
    return tuple(phone.replace("ˈ", "").replace("ˌ", "") for phone in phones)


def without_quantity(phones: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        phone.replace("ˈ", "").replace("ˌ", "").replace("ː", "") for phone in phones
    )


def levenshtein_counts(
    expected: Sequence[str], actual: Sequence[str]
) -> tuple[int, int, int, int]:
    """Return edit distance and substitution, insertion, deletion counts."""
    rows = len(expected) + 1
    cols = len(actual) + 1
    distance = [[0] * cols for _ in range(rows)]
    operations: list[list[str]] = [[""] * cols for _ in range(rows)]
    for row in range(1, rows):
        distance[row][0] = row
        operations[row][0] = "deletion"
    for col in range(1, cols):
        distance[0][col] = col
        operations[0][col] = "insertion"
    for row in range(1, rows):
        for col in range(1, cols):
            if expected[row - 1] == actual[col - 1]:
                distance[row][col] = distance[row - 1][col - 1]
                operations[row][col] = "equal"
                continue
            choices = (
                (distance[row - 1][col - 1] + 1, "substitution"),
                (distance[row][col - 1] + 1, "insertion"),
                (distance[row - 1][col] + 1, "deletion"),
            )
            distance[row][col], operations[row][col] = min(
                choices, key=lambda item: item[0]
            )
    substitutions = insertions = deletions = 0
    row, col = len(expected), len(actual)
    while row or col:
        operation = operations[row][col]
        if operation == "substitution":
            substitutions += 1
            row -= 1
            col -= 1
        elif operation == "insertion":
            insertions += 1
            col -= 1
        elif operation == "deletion":
            deletions += 1
            row -= 1
        else:
            row -= 1
            col -= 1
    return distance[-1][-1], substitutions, insertions, deletions


def levenshtein_distance(expected: Sequence[str], actual: Sequence[str]) -> int:
    return levenshtein_counts(expected, actual)[0]


def compare_case(
    case: ReferenceCase, result: SwedishRuleResult | None = None
) -> CaseComparison:
    result = result or phonemize_word_raw(case.word)
    actual = result.phones
    distance, substitutions, insertions, deletions = levenshtein_counts(
        case.phones, actual
    )
    return CaseComparison(
        case=case,
        actual=actual,
        result=result,
        exact=case.phones == actual,
        stressless_equal=without_stress(case.phones) == without_stress(actual),
        quantityless_equal=without_quantity(case.phones) == without_quantity(actual),
        edit_distance=distance,
        substitutions=substitutions,
        insertions=insertions,
        deletions=deletions,
    )


def feature_tags(word: str, rule_ids: Sequence[str] = ()) -> tuple[str, ...]:  # noqa: C901
    lower = word.casefold()
    tags: list[str] = []

    def add(tag: str) -> None:
        if tag not in tags:
            tags.append(tag)

    soft = set("eiyäöé")
    for spelling, tag in (
        ("sj", "contains_sj"),
        ("skj", "contains_skj"),
        ("stj", "contains_stj"),
        ("sch", "contains_sch"),
        ("tj", "contains_tj"),
        ("kj", "contains_kj"),
        ("dj", "contains_dj"),
        ("gj", "contains_gj"),
        ("hj", "contains_hj"),
        ("lj", "contains_lj"),
        ("ng", "contains_ng"),
        ("x", "contains_x"),
        ("c", "contains_c"),
        ("w", "contains_w"),
    ):
        if spelling in lower:
            add(tag)
    if "sk" in lower:
        add(
            "soft_sk"
            if lower[lower.index("sk") + 2 : lower.index("sk") + 3] in soft
            else "hard_sk"
        )
    for index, char in enumerate(lower[:-1]):
        if char == "g":
            add("soft_g" if lower[index + 1] in soft else "hard_g")
        if char == "k":
            add("soft_k" if lower[index + 1] in soft else "hard_k")
    if any(lower[index] == lower[index + 1] for index in range(len(lower) - 1)):
        add("double_consonant")
    if len(lower) >= 12:
        add("word_len_13_plus" if len(lower) >= 13 else "word_len_9_12")
    if len(lower) <= 4:
        add("word_len_1_4")
    elif len(lower) <= 8:
        add("word_len_5_8")
    for suffix, tag in (
        ("tion", "suffix_tion"),
        ("sion", "suffix_sion"),
        ("itet", "suffix_itet"),
        ("era", "suffix_era"),
        ("ering", "suffix_ering"),
        ("ism", "suffix_ism"),
        ("ist", "suffix_ist"),
    ):
        if lower.endswith(suffix):
            add(tag)
    for target, tag in (
        ("t", "r_before_t"),
        ("d", "r_before_d"),
        ("n", "r_before_n"),
        ("s", "r_before_s"),
        ("l", "r_before_l"),
    ):
        if f"r{target}" in lower:
            add(tag)
    if "é" in lower:
        add("contains_é")
    for vowel in ["a", "e", "i", "o", "u", "å", "ä", "ö"]:
        if vowel in lower:
            add(f"contains_{vowel}")
    for rule_id in rule_ids:
        add(f"rule:{rule_id}")
    return tuple(tags)


def _write_tsv(
    path: Path, header: Sequence[str], rows: Iterable[Sequence[object]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def _format_ipa(phones: Sequence[str]) -> str:
    return "".join(phones)


def _case_row(comparison: CaseComparison, traced: bool) -> tuple[object, ...]:
    result = comparison.result
    return (
        comparison.case.line_number,
        comparison.case.word,
        _format_ipa(comparison.case.phones),
        _format_ipa(comparison.actual),
        int(comparison.exact),
        int(comparison.stressless_equal),
        int(comparison.quantityless_equal),
        comparison.edit_distance,
        len(comparison.case.phones),
        len(comparison.actual),
        ",".join(feature_tags(comparison.case.word)),
        ",".join(result.rule_ids) if traced else "",
    )


def _read_baseline(path: Path) -> tuple[dict[str, tuple[str, ...]], dict[str, object]]:
    directory = path if path.is_dir() else path.parent
    actuals: dict[str, tuple[str, ...]] = {}
    failures = directory / "failures.tsv"
    if failures.exists():
        with failures.open("r", encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle, delimiter="\t"):
                actuals[row["word"]] = tuple(row["actual"])
    summary_path = path if path.is_file() else directory / "summary.json"
    summary: dict[str, object] = {}
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    return actuals, summary


def _inspect_format(path: Path, limit: int) -> None:
    tokens = Counter()
    stress = Counter()
    lengths = []
    samples: list[str] = []
    duplicates: Counter[str] = Counter()
    non_swedish: Counter[str] = Counter()
    for case in iter_reference_cases(path):
        duplicates[case.word] += 1
        tokens.update(case.phones)
        lengths.append(len(case.phones))
        if "ˈ" in "".join(case.phones):
            stress["contains_primary_stress"] += 1
        if "ˌ" in "".join(case.phones):
            stress["contains_secondary_stress"] += 1
        if any(
            char not in "abcdefghijklmnopqrstuvwxyzåäöé-"
            for char in case.word.casefold()
        ):
            non_swedish[case.word] += 1
        if len(samples) < 10:
            samples.append(f"{case.line_number}: {case.word}\t{' '.join(case.phones)}")
        if sum(duplicates.values()) >= limit:
            break
    print("most common token forms:")
    for token, count in tokens.most_common(20):
        print(f"  {token}\t{count}")
    combining_marks = sum(
        count
        for token, count in tokens.items()
        if any(ord(char) >= 0x300 for char in token)
    )
    length_marked = sum(count for token, count in tokens.items() if "ː" in token)
    duplicate_rows = sum(count - 1 for count in duplicates.values() if count > 1)
    print(f"tokens containing combining marks: {combining_marks}")
    print(f"tokens containing ː: {length_marked}")
    print(f"stress token placement: {dict(stress)}")
    print(f"maximum phones/word: {max(lengths, default=0)}")
    print(f"duplicate word rows: {duplicate_rows}")
    print(f"non-Swedish or unexpected words: {len(non_swedish)}")
    print("sample lines:")
    print("\n".join(samples))


def _group_rows(comparisons: Sequence[CaseComparison]) -> list[tuple[object, ...]]:
    grouped: dict[str, list[CaseComparison]] = defaultdict(list)
    for comparison in comparisons:
        tags = feature_tags(comparison.case.word)
        for tag in tags:
            if not tag.startswith("rule:"):
                grouped[tag].append(comparison)
    rows = []
    for tag, cases in grouped.items():
        exact = sum(case.exact for case in cases)
        samples = [case.case.word for case in cases if not case.exact][:3]
        rows.append(
            (
                tag,
                len(cases),
                exact,
                len(cases) - exact,
                100 * exact / len(cases),
                100 * sum(case.stressless_equal for case in cases) / len(cases),
                100 * sum(case.quantityless_equal for case in cases) / len(cases),
                sum(case.edit_distance for case in cases) / len(cases),
                *samples,
            )
        )
    return sorted(rows, key=lambda row: (-row[3], -row[1], str(row[0])))


def _confusion_rows(comparisons: Sequence[CaseComparison]) -> list[tuple[object, ...]]:
    confusion: Counter[tuple[str, str]] = Counter()
    for comparison in comparisons:
        expected, actual = comparison.case.phones, comparison.actual
        row, col = len(expected), len(actual)
        distance = [[0] * (col + 1) for _ in range(row + 1)]
        for i in range(row + 1):
            distance[i][0] = i
        for j in range(col + 1):
            distance[0][j] = j
        for i in range(1, row + 1):
            for j in range(1, col + 1):
                distance[i][j] = min(
                    distance[i - 1][j - 1] + (expected[i - 1] != actual[j - 1]),
                    distance[i][j - 1] + 1,
                    distance[i - 1][j] + 1,
                )
        i, j = row, col
        while i or j:
            if (
                i
                and j
                and distance[i][j]
                == distance[i - 1][j - 1] + (expected[i - 1] != actual[j - 1])
            ):
                if expected[i - 1] != actual[j - 1]:
                    confusion[(expected[i - 1], actual[j - 1])] += 1
                i -= 1
                j -= 1
            elif j and distance[i][j] == distance[i][j - 1] + 1:
                j -= 1
            else:
                i -= 1
    return [
        (expected, actual, count)
        for (expected, actual), count in confusion.most_common()
    ]


def _regression_rows(
    comparisons: Sequence[CaseComparison], baseline_actuals: dict[str, tuple[str, ...]]
) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    improvements: list[tuple[object, ...]] = []
    regressions: list[tuple[object, ...]] = []
    for comparison in comparisons:
        old = baseline_actuals.get(comparison.case.word)
        if old is None:
            continue
        old_distance = levenshtein_distance(comparison.case.phones, old)
        new_distance = comparison.edit_distance
        row = (
            comparison.case.word,
            _format_ipa(old),
            _format_ipa(comparison.actual),
            _format_ipa(comparison.case.phones),
            old_distance,
            new_distance,
            new_distance - old_distance,
        )
        if new_distance < old_distance:
            improvements.append(row)
        elif new_distance > old_distance:
            regressions.append(row)
    return improvements, regressions


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lexicon", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--split", choices=("train", "dev", "test", "all"), default="all"
    )
    parser.add_argument("--sample", type=int)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--pattern")
    parser.add_argument("--prefix")
    parser.add_argument("--suffix")
    parser.add_argument("--only-failures", action="store_true")
    parser.add_argument("--trace-failures", action="store_true")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--fail-on-regression", type=float)
    parser.add_argument("--verify-sha256", action="store_true")
    parser.add_argument("--expected-sha256", default=EXPECTED_SHA256)
    parser.add_argument("--progress-every", type=int, default=0)
    parser.add_argument("--no-stress-metric", action="store_true")
    parser.add_argument("--max-examples-per-group", type=int, default=3)
    parser.add_argument("--inspect-format", type=int, metavar="N")
    return parser.parse_args(argv)


def _resolve_lexicon(argument: Path | None) -> Path:
    if argument is not None:
        return argument
    import os

    value = os.environ.get("KOKOROG2P_SV_LEXICON")
    if value:
        return Path(value)
    raise ValueError("Provide --lexicon PATH or KOKOROG2P_SV_LEXICON")


def run_benchmark(args: argparse.Namespace) -> int:
    path = _resolve_lexicon(args.lexicon)
    if not path.is_file():
        raise ValueError(f"Lexicon does not exist: {path}")
    if args.verify_sha256:
        actual_sha = sha256_file(path)
        if actual_sha != args.expected_sha256:
            message = (
                f"SHA256 mismatch for {path}: expected {args.expected_sha256}, "
                f"got {actual_sha}"
            )
            raise ValueError(message)
    else:
        actual_sha = sha256_file(path)
    if args.inspect_format is not None:
        _inspect_format(path, args.inspect_format)
        return 0

    output = args.output or Path("benchmarks/results/sv") / time.strftime(
        "run-%Y%m%d-%H%M%S"
    )
    output.mkdir(parents=True, exist_ok=True)
    selected: list[ReferenceCase] = []
    for case in iter_reference_cases(path):
        if args.split != "all" and stable_split(case.word) != args.split:
            continue
        if args.pattern and args.pattern not in case.word:
            continue
        if args.prefix and not case.word.startswith(args.prefix):
            continue
        if args.suffix and not case.word.endswith(args.suffix):
            continue
        selected.append(case)
        if args.limit is not None and len(selected) >= args.limit:
            break
    if args.sample is not None and len(selected) > args.sample:
        random.Random(args.seed).shuffle(selected)
        selected = selected[: args.sample]

    start = time.perf_counter()
    comparisons: list[CaseComparison] = []
    passed = failed = 0
    distance_total = substitutions = insertions = deletions = 0
    split_counts = Counter()
    for index, case in enumerate(selected, 1):
        comparison = compare_case(case)
        if args.only_failures and comparison.exact:
            continue
        if not comparison.exact and args.trace_failures:
            comparison = compare_case(case, phonemize_word_raw(case.word, trace=True))
        comparisons.append(comparison)
        passed += comparison.exact
        failed += not comparison.exact
        distance_total += comparison.edit_distance
        substitutions += comparison.substitutions
        insertions += comparison.insertions
        deletions += comparison.deletions
        split_counts[stable_split(case.word)] += 1
        if args.progress_every and index % args.progress_every == 0:
            print(f"processed {index} rows", file=sys.stderr)
    elapsed = time.perf_counter() - start

    failures = [comparison for comparison in comparisons if not comparison.exact]
    _write_tsv(
        output / "failures.tsv",
        FAILURE_HEADER,
        (_case_row(case, args.trace_failures) for case in failures),
    )
    _write_tsv(
        output / "groups.tsv",
        (
            "feature",
            "cases",
            "exact",
            "failed",
            "exact_percent",
            "stressless_percent",
            "quantityless_percent",
            "mean_edit_distance",
            "sample_failure_1",
            "sample_failure_2",
            "sample_failure_3",
        ),
        _group_rows(comparisons),
    )
    _write_tsv(
        output / "confusions.tsv",
        ("expected", "actual", "count"),
        _confusion_rows(comparisons),
    )
    _write_tsv(
        output / "rule_coverage.tsv",
        ("rule_id", "description", "fired", "passed", "failed", "failure_rate"),
        _coverage_rows(comparisons),
    )
    _write_tsv(
        output / "stress_failures.tsv",
        (
            "word",
            "expected",
            "actual",
            "expected_primary_position",
            "actual_primary_position",
            "features",
        ),
        _stress_rows(comparisons),
    )
    _write_tsv(
        output / "quantity_failures.tsv",
        ("word", "expected", "actual", "features"),
        _quantity_rows(comparisons),
    )
    _write_tsv(
        output / "prefixes.tsv",
        (
            "affix",
            "length",
            "cases",
            "failures",
            "failure_rate",
            "mean_edit_distance",
            "sample_words",
        ),
        _affix_rows(comparisons, prefix=True),
    )
    _write_tsv(
        output / "suffixes.tsv",
        (
            "affix",
            "length",
            "cases",
            "failures",
            "failure_rate",
            "mean_edit_distance",
            "sample_words",
        ),
        _affix_rows(comparisons, prefix=False),
    )
    _write_tsv(
        output / "ngrams.tsv",
        ("ngram", "cases", "failures", "failure_rate", "enrichment"),
        _ngram_rows(comparisons),
    )

    baseline_actuals: dict[str, tuple[str, ...]] = {}
    baseline_summary: dict[str, object] = {}
    if args.baseline:
        baseline_actuals, baseline_summary = _read_baseline(args.baseline)
    improvements, regressions = _regression_rows(comparisons, baseline_actuals)
    regression_header = (
        "word",
        "old_actual",
        "new_actual",
        "expected",
        "old_distance",
        "new_distance",
        "delta",
    )
    _write_tsv(output / "improvements.tsv", regression_header, improvements)
    _write_tsv(output / "regressions.tsv", regression_header, regressions)

    case_count = len(comparisons)
    metrics = {
        "cases": case_count,
        "exact": passed,
        "exact_percent": 100 * passed / case_count if case_count else 0.0,
        "stressless": sum(case.stressless_equal for case in comparisons),
        "stressless_percent": 100
        * sum(case.stressless_equal for case in comparisons)
        / case_count
        if case_count
        else 0.0,
        "quantityless": sum(case.quantityless_equal for case in comparisons),
        "quantityless_percent": 100
        * sum(case.quantityless_equal for case in comparisons)
        / case_count
        if case_count
        else 0.0,
        "phone_error_rate": distance_total
        / sum(len(case.case.phones) for case in comparisons)
        if comparisons
        else 0.0,
        "substitutions": substitutions,
        "insertions": insertions,
        "deletions": deletions,
    }
    summary = {
        "schema": 1,
        "lexicon": {
            "path": str(path),
            "sha256": actual_sha,
            "rows_seen": len(selected),
        },
        "rules": {"engine_version": "sv-rules-v0.1"},
        "split": args.split,
        "split_counts": dict(split_counts),
        "metrics": metrics,
        "timing": {
            "seconds": elapsed,
            "words_per_second": len(selected) / elapsed if elapsed else 0.0,
        },
        "baseline": baseline_summary,
        "regressions": {
            "improvements": len(improvements),
            "regressions": len(regressions),
        },
    }
    (output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.fail_on_regression is not None and baseline_summary:
        old_metrics = baseline_summary.get("metrics", {})
        old_exact = float(old_metrics.get("exact_percent", 0.0))
        if old_exact - metrics["exact_percent"] > args.fail_on_regression * 100:
            return 1
    return 0


def _coverage_rows(comparisons: Sequence[CaseComparison]) -> list[tuple[object, ...]]:
    fired: dict[str, list[bool]] = defaultdict(list)
    for comparison in comparisons:
        for rule_id in comparison.result.rule_ids:
            fired[rule_id].append(comparison.exact)
    return [
        (
            rule,
            rule,
            len(values),
            sum(values),
            len(values) - sum(values),
            (len(values) - sum(values)) / len(values),
        )
        for rule, values in sorted(fired.items())
    ]


def _stress_rows(comparisons: Sequence[CaseComparison]) -> list[tuple[object, ...]]:
    rows = []
    for comparison in comparisons:
        if not (comparison.stressless_equal and not comparison.exact):
            continue
        expected_position = next(
            (
                index
                for index, phone in enumerate(comparison.case.phones)
                if "ˈ" in phone
            ),
            -1,
        )
        actual_position = next(
            (index for index, phone in enumerate(comparison.actual) if "ˈ" in phone), -1
        )
        rows.append(
            (
                comparison.case.word,
                _format_ipa(comparison.case.phones),
                _format_ipa(comparison.actual),
                expected_position,
                actual_position,
                ",".join(feature_tags(comparison.case.word)),
            )
        )
    return rows


def _quantity_rows(comparisons: Sequence[CaseComparison]) -> list[tuple[object, ...]]:
    return [
        (
            case.case.word,
            _format_ipa(case.case.phones),
            _format_ipa(case.actual),
            ",".join(feature_tags(case.case.word)),
        )
        for case in comparisons
        if case.quantityless_equal and not case.stressless_equal
    ]


def _affix_rows(
    comparisons: Sequence[CaseComparison], *, prefix: bool
) -> list[tuple[object, ...]]:
    grouped: dict[str, list[CaseComparison]] = defaultdict(list)
    for comparison in comparisons:
        word = comparison.case.word.casefold()
        for length in range(2, 7):
            affix = word[:length] if prefix else word[-length:]
            grouped[affix].append(comparison)
    rows = []
    for affix, cases in grouped.items():
        failures = sum(not case.exact for case in cases)
        if len(cases) < 2:
            continue
        rows.append(
            (
                affix,
                len(affix),
                len(cases),
                failures,
                failures / len(cases),
                sum(case.edit_distance for case in cases) / len(cases),
                ",".join(case.case.word for case in cases[:3]),
            )
        )
    return sorted(rows, key=lambda row: (-row[3], -row[2], row[0]))


def _ngram_rows(comparisons: Sequence[CaseComparison]) -> list[tuple[object, ...]]:
    totals: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    for comparison in comparisons:
        word = comparison.case.word.casefold()
        ngrams = {
            word[index : index + size]
            for size in range(1, 5)
            for index in range(len(word) - size + 1)
        }
        totals.update(ngrams)
        if not comparison.exact:
            failures.update(ngrams)
    rows = []
    overall = (
        sum(not comparison.exact for comparison in comparisons) / len(comparisons)
        if comparisons
        else 0.0
    )
    for ngram, cases in totals.items():
        if cases < 2:
            continue
        failure_rate = failures[ngram] / cases
        rows.append(
            (
                ngram,
                cases,
                failures[ngram],
                failure_rate,
                failure_rate / overall if overall else 0.0,
            )
        )
    return sorted(rows, key=lambda row: (-row[4], -row[1], row[0]))


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return run_benchmark(_parse_args(argv))
    except (OSError, ValueError, csv.Error) as exc:
        print(f"benchmark_sv_rules.py: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
