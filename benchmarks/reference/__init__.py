"""Reference compatibility benchmarking for KokoroG2P."""

from .candidate import CANDIDATE_PROFILES, analyze_model_encoding, run_candidate
from .compare import compare_results, compare_case_results
from .corpus import load_corpus, load_case_data
from .providers import (
    HexgradEnglishMisakiProvider,
    SemidarkGermanMisakiProvider,
    unavailable_provider,
)
from .registry import CANDIDATE_REGISTRY, REFERENCE_PROFILES, get_reference_provider
from .report import render_json, render_markdown
from .types import (
    BenchmarkReport,
    CandidateOutput,
    CandidateProfile,
    CaseComparison,
    ComparisonSummary,
    CorpusCase,
    EncodingAnalysis,
    ErrorInfo,
    ReferenceMetadata,
    ReferenceOutput,
)

__all__ = [
    "CANDIDATE_PROFILES",
    "CANDIDATE_REGISTRY",
    "REFERENCE_PROFILES",
    "BenchmarkReport",
    "CandidateOutput",
    "CandidateProfile",
    "CaseComparison",
    "ComparisonSummary",
    "CorpusCase",
    "EncodingAnalysis",
    "ErrorInfo",
    "HexgradEnglishMisakiProvider",
    "ReferenceMetadata",
    "ReferenceOutput",
    "SemidarkGermanMisakiProvider",
    "analyze_model_encoding",
    "compare_case_results",
    "compare_results",
    "get_reference_provider",
    "load_case_data",
    "load_corpus",
    "render_json",
    "render_markdown",
    "run_candidate",
    "unavailable_provider",
]
