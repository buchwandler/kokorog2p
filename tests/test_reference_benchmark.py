from __future__ import annotations

import json

import pytest

from benchmarks.benchmark_reference import _should_fail, main
from benchmarks.reference.compare import _symbol_diff, compare_results
from benchmarks.reference.corpus import load_corpus
from benchmarks.reference.golden import load_reference_golden
from benchmarks.reference.report import render_json, render_markdown, render_summary
from benchmarks.reference.types import (
    BenchmarkReport,
    CandidateOutput,
    CandidateProfile,
    Corpus,
    CorpusCase,
    EncodingAnalysis,
    ErrorInfo,
    ReferenceMetadata,
    ReferenceOutput,
)


def _metadata() -> ReferenceMetadata:
    return ReferenceMetadata(
        "fake-provider", "example/fake", "abcdef1234567", "1.0", "fake.G2P"
    )


def _case(case_id: str, text: str = "hello", policy: str = "diagnostic") -> CorpusCase:
    return CorpusCase(case_id, text, policy=policy)


def _encoding(token_ids: tuple[int, ...] = (43,)) -> EncodingAnalysis:
    return EncodingAnalysis(True, (), token_ids, "a", False)


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
    assert '"identity"' in serialized
    assert "accuracy" not in render_markdown(report).lower()


def test_mutable_reference_revision_is_rejected() -> None:
    with pytest.raises(ValueError, match="immutable"):
        ReferenceMetadata("fake", "example/fake", "main", "1.0", "fake.G2P")


def test_all_case_policies_are_evaluated() -> None:
    cases = [
        _case("exact", policy="exact"),
        _case("normalized", policy="normalized"),
        _case("model-id", policy="model-id"),
        _case("model-valid", policy="model-valid"),
        _case("diagnostic", policy="diagnostic"),
    ]
    candidate = [
        CandidateOutput(
            item.id, item.text, phonemes="a", token_ids=(43,), encoding=_encoding()
        )
        for item in cases
    ]
    reference = [ReferenceOutput(item.id, item.text, phonemes="a") for item in cases]
    summary = compare_results(cases, candidate, reference)
    assert [item.policy_passed for item in summary.cases] == [
        True,
        True,
        True,
        True,
        None,
    ]
    assert summary.policy_cases == 4
    assert summary.policy_passed == 4
    assert summary.policy_failed == 0
    assert summary.diagnostic_cases == 1


def test_policy_failure_and_regression_gate() -> None:
    case = _case("exact", policy="exact")
    summary = compare_results(
        [case],
        [
            CandidateOutput(
                "exact", "hello", phonemes="a", token_ids=(1,), encoding=_encoding()
            )
        ],
        [ReferenceOutput("exact", "hello", phonemes="b")],
    )
    report = BenchmarkReport(
        CandidateProfile("fake", "en-us"),
        _metadata(),
        Corpus("fake", (case,)),
        summary,
        verdict="fail",
    )
    assert summary.policy_failed == 1
    assert _should_fail(report, "regression") is True


def test_candidate_api_ids_are_an_explicit_health_invariant() -> None:
    case = _case("one", policy="diagnostic")
    summary = compare_results(
        [case],
        [
            CandidateOutput(
                "one", "hello", phonemes="a", token_ids=(2,), encoding=_encoding((1,))
            )
        ],
        [ReferenceOutput("one", "hello", phonemes="a")],
    )
    assert summary.candidate_api_id_mismatches == 1
    assert summary.cases[0].candidate_api_ids_consistent is False


def test_diagnostic_difference_is_non_gating() -> None:
    case = _case("diagnostic", policy="diagnostic")
    summary = compare_results(
        [case],
        [
            CandidateOutput(
                "diagnostic",
                "hello",
                phonemes="a",
                token_ids=(43,),
                encoding=_encoding(),
            )
        ],
        [ReferenceOutput("diagnostic", "hello", phonemes="b")],
    )
    report = BenchmarkReport(
        CandidateProfile("fake", "en-us"), _metadata(), Corpus("fake", (case,)), summary
    )
    assert summary.policy_failed == 0
    assert summary.diagnostic_differences == 1
    assert report.verdict == "pass"
    assert _should_fail(report, "regression") is False


def test_true_levenshtein_diff_counts() -> None:
    assert _symbol_diff("abc", "adc").edit_distance == 1
    assert _symbol_diff("abc", "abcd").insertions == 1
    assert _symbol_diff("abcd", "acd").deletions == 1
    assert _symbol_diff("", "abc").edit_distance == 3


def test_committed_goldens_validate_without_live_reference() -> None:
    for reference_id in ("hexgrad-en-us-v1", "hexgrad-en-gb-v1", "semidark-de-v1"):
        golden = load_reference_golden(reference_id)
        assert golden.outputs
        assert all(output.error is None for output in golden.outputs)


def test_summary_renderer_reports_verdict_first() -> None:
    case = _case("one", policy="exact")
    summary = compare_results(
        [case],
        [CandidateOutput("one", "hello", phonemes="a")],
        [ReferenceOutput("one", "hello", phonemes="b")],
    )
    report = BenchmarkReport(
        CandidateProfile("fake", "en-us"),
        _metadata(),
        Corpus("fake", (case,)),
        summary,
        verdict="fail",
    )
    rendered = render_summary(report)
    assert rendered.startswith("[FAIL]")
    assert "Failures:" in rendered


def test_json_alias_is_one_document(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "--reference",
            "hexgrad-en-us-v1",
            "--candidate",
            "en-us-default",
            "--reference-source",
            "golden",
            "--case",
            "en-us-basic-doctor-001",
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    assert json.loads(captured.out)["verdict"] == "pass"
    assert captured.err == ""
