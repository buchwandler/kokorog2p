from __future__ import annotations

import pytest

from benchmarks.reference.compare import compare_results
from benchmarks.reference.corpus import load_corpus
from benchmarks.reference.report import render_json, render_markdown
from benchmarks.reference.types import (
    BenchmarkReport,
    CandidateOutput,
    CandidateProfile,
    Corpus,
    CorpusCase,
    ErrorInfo,
    ReferenceMetadata,
    ReferenceOutput,
)


def _metadata() -> ReferenceMetadata:
    return ReferenceMetadata(
        "fake-provider", "example/fake", "abcdef1234567", "1.0", "fake.G2P"
    )


def _case(case_id: str, text: str = "hello") -> CorpusCase:
    return CorpusCase(case_id, text, policy="diagnostic")


def _compare(
    candidate: list[CandidateOutput],
    reference: list[ReferenceOutput],
    cases: list[CorpusCase] | None = None,
):
    cases = cases or [_case(item.case_id, item.input_text) for item in candidate]
    return compare_results(cases, candidate, reference, sample_limit=1)


def test_reviewed_corpora_are_stable_and_tagged() -> None:
    english = load_corpus("en-us")
    german = load_corpus("de")
    assert english.cases[0].id == "en-us-basic-hello-001"
    assert any("historical-regression" in case.tags for case in german.cases)


def test_exact_and_normalized_agreement_are_independent() -> None:
    cases = [_case("one"), _case("two")]
    candidate = [
        CandidateOutput("one", "hello", phonemes="hˈɛlO"),
        CandidateOutput("two", "hello", phonemes="hˈɛlO  "),
    ]
    reference = [
        ReferenceOutput("one", "hello", phonemes="hˈɛlO"),
        ReferenceOutput("two", "hello", phonemes="hˈɛlO"),
    ]
    summary = compare_results(cases, candidate, reference)
    assert summary.exact_phoneme_matches == 1
    assert summary.normalized_phoneme_matches == 2
    assert summary.difference_count == 1
    assert len(summary.difference_samples) == 1


def test_difference_count_is_not_truncated() -> None:
    cases = [_case(str(index), str(index)) for index in range(4)]
    candidate = [CandidateOutput(case.id, case.text, phonemes="a") for case in cases]
    reference = [ReferenceOutput(case.id, case.text, phonemes="b") for case in cases]
    summary = compare_results(cases, candidate, reference, sample_limit=2)
    assert summary.difference_count == 4
    assert len(summary.difference_samples) == 2


def test_failures_never_count_as_agreement() -> None:
    cases = [_case("candidate-error"), _case("reference-error"), _case("both-error")]
    candidate = [
        CandidateOutput(
            "candidate-error", "hello", error=ErrorInfo("Error", "candidate")
        ),
        CandidateOutput("reference-error", "hello", phonemes="a"),
        CandidateOutput("both-error", "hello", error=ErrorInfo("Error", "candidate")),
    ]
    reference = [
        ReferenceOutput("candidate-error", "hello", phonemes=""),
        ReferenceOutput(
            "reference-error", "hello", error=ErrorInfo("Error", "reference")
        ),
        ReferenceOutput("both-error", "hello", error=ErrorInfo("Error", "reference")),
    ]
    summary = compare_results(cases, candidate, reference)
    assert summary.exact_phoneme_matches == 0
    assert summary.difference_count == 3
    assert {item.classification for item in summary.cases} == {
        "candidate-error",
        "reference-error",
    }


def test_structural_case_errors_are_rejected() -> None:
    cases = [_case("one")]
    with pytest.raises(ValueError, match="missing"):
        compare_results(cases, [], [ReferenceOutput("one", "hello", phonemes="a")])
    with pytest.raises(ValueError, match="duplicate"):
        compare_results(
            cases,
            [
                CandidateOutput("one", "hello", phonemes="a"),
                CandidateOutput("one", "hello", phonemes="a"),
            ],
            [ReferenceOutput("one", "hello", phonemes="a")],
        )


def test_metadata_and_report_serialization() -> None:
    metadata = _metadata()
    report = BenchmarkReport(
        CandidateProfile("fake", "en-us"),
        metadata,
        Corpus("fake", (_case("one"),)),
        _compare(
            [CandidateOutput("one", "hello", phonemes="a")],
            [ReferenceOutput("one", "hello", phonemes="a")],
        ),
    )
    serialized = render_json(report)
    assert '"provider_id": "fake-provider"' in serialized
    assert "accuracy" not in render_markdown(report).lower()


def test_mutable_reference_revision_is_rejected() -> None:
    with pytest.raises(ValueError, match="immutable"):
        ReferenceMetadata("fake", "example/fake", "main", "1.0", "fake.G2P")
