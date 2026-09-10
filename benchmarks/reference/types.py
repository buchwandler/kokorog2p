"""Stable data types used by the reference benchmark."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any, Literal, Protocol

SCHEMA_VERSION = 2
MUTABLE_REVISIONS = {"main", "master", "latest", "head", "unknown", ""}
Verdict = Literal["pass", "fail", "error"]


def _json_value(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_json_value(item) for item in value]
    return value


class ReferenceBenchmarkError(Exception):
    """Base error for benchmark configuration or result failures."""


@dataclass(frozen=True)
class ErrorInfo:
    type: str
    message: str
    phase: str | None = None

    @classmethod
    def from_exception(cls, exc: BaseException, phase: str | None = None) -> ErrorInfo:
        return cls(type(exc).__name__, str(exc), phase)

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class ReferenceMetadata:
    provider_id: str
    repository: str
    commit: str
    package_version: str
    frontend: str
    configuration: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.provider_id or self.provider_id == "misaki":
            raise ValueError("provider_id must identify a concrete reference provider")
        if not self.repository:
            raise ValueError("repository is required")
        if self.commit.lower() in MUTABLE_REVISIONS or not re.fullmatch(
            r"[0-9a-fA-F]{7,40}", self.commit
        ):
            raise ValueError("reference metadata requires an immutable commit SHA")
        if not self.package_version:
            raise ValueError("package_version is required")
        if not self.frontend:
            raise ValueError("frontend is required")

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class CandidateProfile:
    id: str
    language: str
    target_model: str = "1.0"
    backend: str = "kokorog2p"
    lexicons: tuple[str, ...] | None = None
    fallback: str = "espeak"
    use_spacy: bool | None = None
    spacy_model: str | None = None
    use_goruut_fallback: bool = False

    def __post_init__(self) -> None:
        if not self.id or not self.language:
            raise ValueError("candidate id and language are required")
        if self.fallback not in {"none", "espeak", "goruut"}:
            raise ValueError(f"unsupported fallback: {self.fallback}")

    @property
    def configuration(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "target_model": self.target_model,
            "backend": self.backend,
            "lexicons": list(self.lexicons) if self.lexicons is not None else None,
            "fallback": self.fallback,
            "use_spacy": self.use_spacy,
            "spacy_model": self.spacy_model,
            "use_goruut_fallback": self.use_goruut_fallback,
        }

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class CorpusCase:
    id: str
    text: str
    policy: str = "diagnostic"
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or not self.text:
            raise ValueError("corpus case id and text are required")
        if self.policy not in {
            "exact",
            "normalized",
            "model-id",
            "model-valid",
            "diagnostic",
        }:
            raise ValueError(f"unsupported case policy: {self.policy}")

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class Corpus:
    id: str
    cases: tuple[CorpusCase, ...]
    revision: str = "1"
    generated: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("corpus case IDs must be unique")

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class EncodingAnalysis:
    valid: bool
    invalid_symbols: tuple[str, ...]
    token_ids: tuple[int, ...]
    decoded: str
    encoding_loss: bool

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class ReferenceOutput:
    case_id: str
    input_text: str
    normalized_text: str | None = None
    phonemes: str = ""
    error: ErrorInfo | None = None
    encoding: EncodingAnalysis | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class CandidateOutput:
    case_id: str
    input_text: str
    clean_text: str | None = None
    phonemes: str = ""
    token_ids: tuple[int, ...] = ()
    encoding: EncodingAnalysis | None = None
    warnings: tuple[str, ...] = ()
    language_routes: tuple[Mapping[str, Any], ...] = ()
    error: ErrorInfo | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class SymbolDiff:
    insertions: int
    deletions: int
    substitutions: int
    first_difference: int | None
    edit_distance: int

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class CaseComparison:
    case_id: str
    input_text: str
    policy: str
    policy_passed: bool | None
    candidate_ok: bool
    reference_ok: bool
    exact_phoneme_match: bool
    normalized_phoneme_match: bool
    model_symbol_match: bool
    model_id_match: bool | None
    symbol_diff: SymbolDiff
    classification: str
    candidate: CandidateOutput
    reference: ReferenceOutput
    candidate_api_ids_consistent: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class ComparisonSummary:
    cases: tuple[CaseComparison, ...]
    difference_count: int
    difference_samples: tuple[CaseComparison, ...]
    cases_total: int
    candidate_success: int
    reference_success: int
    comparable_cases: int
    exact_phoneme_matches: int
    normalized_phoneme_matches: int
    model_symbol_matches: int
    model_id_matches: int
    candidate_encoding_failures: int
    reference_encoding_failures: int
    candidate_encoding_loss: int
    reference_encoding_loss: int
    policy_cases: int = 0
    policy_passed: int = 0
    policy_failed: int = 0
    diagnostic_cases: int = 0
    diagnostic_differences: int = 0
    candidate_errors: int = 0
    reference_errors: int = 0
    candidate_api_id_mismatches: int = 0
    model_id_comparable_cases: int = 0
    classification_counts: Mapping[str, int] = field(default_factory=dict)
    policy_counts: Mapping[str, int] = field(default_factory=dict)
    policy_failure_counts: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


@dataclass(frozen=True)
class BenchmarkReport:
    candidate: CandidateProfile
    reference: ReferenceMetadata
    corpus: Corpus
    summary: ComparisonSummary
    schema_version: int = SCHEMA_VERSION
    benchmark_kind: str = "reference"
    performance: Mapping[str, Any] | None = None
    verdict: Verdict = "pass"
    reference_source: str = "live"
    execution: Mapping[str, Any] = field(default_factory=dict)
    baseline: Mapping[str, Any] | None = None

    @property
    def identity(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "reference": self.reference.to_dict(),
            "reference_source": self.reference_source,
            "corpus_id": self.corpus.id,
            "corpus_revision": self.corpus.revision,
            "case_ids": [case.id for case in self.corpus.cases],
            "target_model": self.candidate.target_model,
        }

    def to_dict(self) -> dict[str, Any]:
        result = _json_value(self)
        result["identity"] = self.identity
        return result


@dataclass(frozen=True)
class BenchmarkSuiteReport:
    suite: str
    reports: tuple[BenchmarkReport, ...]
    verdict: Verdict
    schema_version: int = SCHEMA_VERSION
    benchmark_kind: str = "reference-suite"

    def to_dict(self) -> dict[str, Any]:
        return _json_value(self)


class ReferenceProvider(Protocol):
    @property
    def metadata(self) -> ReferenceMetadata: ...

    def prepare(self) -> None: ...

    def phonemize(
        self, text: str, *, case_id: str, language: str, model: str
    ) -> ReferenceOutput: ...


def as_json(value: Any) -> Any:
    """Return a JSON-compatible representation of a benchmark value."""
    return _json_value(value)
