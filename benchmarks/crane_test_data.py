"""Reusable infrastructure for the pinned Crane held-out G2P benchmark."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
import unicodedata
import urllib.request
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kokorog2p.token import GToken

CRANE_REPO = "crane-local-ai/test-data"
CRANE_REVISION = "19b6ea610af45d9258a3957c7a22694280bdf145"
DEFAULT_CACHE_DIR = (
    Path.home() / ".cache" / "kokorog2p" / "benchmarks" / "crane-test-data"
)


@dataclass(frozen=True)
class CraneLanguageConfig:
    public_code: str
    hf_code: str
    kokorog2p_code: str
    test_path: str
    normalizer_ref_path: str
    expected_entries: int = 5000


LANGUAGES: dict[str, CraneLanguageConfig] = {
    "en_US": CraneLanguageConfig(
        "en_US",
        "en_us",
        "en-us",
        "g2p/en_us/test.tsv",
        "g2p/en_us/kokoro_normalizer_ref.tsv",
    ),
    "de_DE": CraneLanguageConfig(
        "de_DE",
        "de_de",
        "de-de",
        "g2p/de_de/test.tsv",
        "g2p/de_de/kokoro_normalizer_ref.tsv",
    ),
}

# These are the SHA-256 values of the files at CRANE_REVISION.
ASSET_SHA256: dict[str, str] = {
    "g2p/kokoro_vocab.json": (
        "02762226a6edbbfb28295d0617b333484bf821a3785a59f3cc4b8d1f32a6f2cf"
    ),
    "g2p/en_us/test.tsv": (
        "3a9adc0a30ea7c8be5cadd91f38020b2f4b4e44130cf00c4a43a5034ca35aa1c"
    ),
    "g2p/de_de/test.tsv": (
        "0dd924798e6f66ef207f9e48be3d9da56cd7212234445dd9102e05093ba0d29d"
    ),
    "g2p/en_us/kokoro_normalizer_ref.tsv": (
        "03d68fe6179feeb4130bfae4d34c747646106908a5efe614ca77145ad06cacd5"
    ),
    "g2p/de_de/kokoro_normalizer_ref.tsv": (
        "40e2ba2678e855c323351decbf0f57cab9ba0c7f38bc41986c04d816db9382b3"
    ),
}


@dataclass(frozen=True)
class BenchmarkEntry:
    word: str
    expected_raw_ipa: str
    line_number: int


@dataclass(frozen=True)
class NormalizerReference:
    raw_ipa: str
    expected_normalized: str
    expected_ids: tuple[int, ...]
    line_number: int = 0


@dataclass(frozen=True)
class NormalizerMismatch:
    line_number: int
    raw_ipa: str
    expected_normalized: str
    actual_normalized: str
    expected_ids: tuple[int, ...]
    actual_ids: tuple[int, ...]
    reason: str


@dataclass(frozen=True)
class NormalizerValidation:
    cases: int
    mismatches: tuple[NormalizerMismatch, ...]

    @property
    def mismatch_count(self) -> int:
        return len(self.mismatches)


@dataclass(frozen=True)
class EntryResult:
    word: str
    expected_raw_ipa: str
    expected_kokoro: str
    actual_kokoro: str
    edit_distance: int
    reference_characters: int
    exact_match: bool
    error: str | None

    @property
    def per_entry_cer(self) -> float:
        if self.reference_characters:
            return self.edit_distance / self.reference_characters
        return 0.0 if not self.actual_kokoro else 1.0


@dataclass(frozen=True)
class LanguageBenchmarkResult:
    language: str
    entries: int
    exact_matches: int
    exact_match_rate: float
    total_edit_distance: int
    reference_characters: int
    cer: float
    exceptions: int
    elapsed_seconds: float
    words_per_second: float
    normalizer_cases: int
    normalizer_mismatches: int
    worst_cases: tuple[EntryResult, ...]


class CraneBenchmarkError(RuntimeError):
    """Base class for benchmark infrastructure failures."""


class MissingDataError(CraneBenchmarkError):
    """Raised when the caller did not provide the external fixture."""


def dataset_url(relative_path: str) -> str:
    """Build a URL containing the immutable dataset revision."""
    return f"https://huggingface.co/datasets/{CRANE_REPO}/raw/{CRANE_REVISION}/{relative_path}"


def _required_paths(configs: Sequence[CraneLanguageConfig]) -> list[str]:
    paths = ["g2p/kokoro_vocab.json"]
    for config in configs:
        paths.extend((config.test_path, config.normalizer_ref_path))
    return list(dict.fromkeys(paths))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_asset(path: Path, relative_path: str) -> None:
    """Verify one asset against the checksum for the pinned revision."""
    expected = ASSET_SHA256[relative_path]
    actual = _sha256(path)
    if actual != expected:
        raise CraneBenchmarkError(
            f"Checksum mismatch for {relative_path}: expected {expected}, got {actual}"
        )


def verify_assets(data_root: Path, configs: Sequence[CraneLanguageConfig]) -> None:
    """Verify all assets needed by the selected languages."""
    for relative_path in _required_paths(configs):
        path = data_root / relative_path
        if not path.is_file():
            raise MissingDataError(f"Crane benchmark data is missing: {path}")
        verify_asset(path, relative_path)


def _download_asset(data_root: Path, relative_path: str) -> None:
    target = data_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        urllib.request.urlretrieve(dataset_url(relative_path), temporary)
        verify_asset(temporary, relative_path)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def resolve_data_root(
    data_root: Path | None,
    *,
    download: bool,
    cache_dir: Path | None = None,
    configs: Sequence[CraneLanguageConfig] | None = None,
) -> Path:
    """Resolve a local checkout or explicitly populate the pinned cache."""
    selected = tuple(configs or LANGUAGES.values())
    root = (
        Path(data_root)
        if data_root is not None
        else Path(cache_dir or DEFAULT_CACHE_DIR) / CRANE_REVISION
    )
    missing = [
        path for path in _required_paths(selected) if not (root / path).is_file()
    ]
    if missing and not download:
        expected = "\n".join(f"  {root / path}" for path in missing)
        raise MissingDataError(
            "Crane benchmark data is missing.\n\n"
            f"Expected:\n{expected}\n\n"
            "Either:\n"
            "  1. pass --data-root /path/to/crane-test-data\n"
            "  2. rerun with --download"
        )
    if download:
        for relative_path in _required_paths(selected):
            path = root / relative_path
            if not path.is_file() or _sha256(path) != ASSET_SHA256[relative_path]:
                _download_asset(root, relative_path)
    verify_assets(root, selected)
    return root


def load_vocab(path: Path) -> dict[str, int]:
    """Load the Crane Kokoro character-to-token vocabulary."""
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict) or any(
        not isinstance(key, str) or not isinstance(token_id, int)
        for key, token_id in value.items()
    ):
        raise ValueError(
            f"{path}: expected a JSON object mapping characters to integer IDs"
        )
    return value


def load_test_tsv(path: Path) -> list[BenchmarkEntry]:
    """Load a strict, headerless word-to-IPA TSV."""
    entries: list[BenchmarkEntry] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 2:
                raise ValueError(
                    f"{path}:{line_number}: expected 2 tab-separated fields, "
                    f"got {len(fields)}"
                )
            word, ipa = fields
            if not word:
                raise ValueError(f"{path}:{line_number}: empty spelling")
            entries.append(BenchmarkEntry(word, ipa, line_number))
    return entries


def _parse_ids(value: str, path: Path, line_number: int) -> tuple[int, ...]:
    if not value:
        return ()
    try:
        return tuple(int(part) for part in value.split(","))
    except ValueError as exc:
        raise ValueError(
            f"{path}:{line_number}: invalid comma-separated token IDs: {value!r}"
        ) from exc


def load_normalizer_ref(path: Path) -> list[NormalizerReference]:
    """Load a strict, headerless raw-IPA normalization reference TSV."""
    references: list[NormalizerReference] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for line_number, line in enumerate(handle, 1):
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 3:
                raise ValueError(
                    f"{path}:{line_number}: expected 3 tab-separated fields, "
                    f"got {len(fields)}"
                )
            raw_ipa, expected_normalized, expected_ids = fields
            references.append(
                NormalizerReference(
                    raw_ipa,
                    expected_normalized,
                    _parse_ids(expected_ids, path, line_number),
                    line_number,
                )
            )
    return references


_SHARED_REPLACEMENTS = {
    "t͡ʃ": "ʧ",
    "d͡ʒ": "ʤ",
    "tʃ": "ʧ",
    "dʒ": "ʤ",
    "eɪ": "A",
    "aɪ": "I",
    "aʊ": "W",
    "oʊ": "O",
    "əʊ": "Q",
    "ɔɪ": "Y",
    "ɝ": "ɜɹ",
    "ɚ": "əɹ",
}
_GERMAN_REPLACEMENTS = {
    "t͡s": "ʦ",
    "d͡z": "ʣ",
    "ts": "ʦ",
    "dz": "ʣ",
    "aʊ̯": "W",
    "aɪ̯": "I",
    "ɔʏ̯": "ɔy",
    "aʊ": "W",
    "aɪ": "I",
    "ss": "S",
    "ʏ": "y",
    "tʃ": "ʧ",
    "dʒ": "ʤ",
    "n̩": "n",
    "l̩": "l",
}


def _replace_longest(value: str, replacements: Mapping[str, str]) -> str:
    for source in sorted(replacements, key=len, reverse=True):
        value = value.replace(source, replacements[source])
    return value


def normalize_reference_ipa(
    raw_ipa: str,
    *,
    language: str,
    vocab: Mapping[str, int],
) -> str:
    """Convert raw Crane IPA into the expected Kokoro character representation."""
    replacements = dict(_SHARED_REPLACEMENTS)
    if language == "de_DE":
        replacements.update(_GERMAN_REPLACEMENTS)
    value = _replace_longest(unicodedata.normalize("NFC", raw_ipa), replacements)
    chars: list[str] = []
    for char in value:
        if char.isspace():
            chars.append(" ")
        elif char in vocab:
            chars.append(char)
    return " ".join("".join(chars).split())


def canonicalize_actual(value: str) -> str:
    """Apply only representation-neutral cleanup to package output."""
    return " ".join(unicodedata.normalize("NFC", value).split())


def validate_reference_normalizer(
    references: Sequence[NormalizerReference],
    *,
    language: str,
    vocab: Mapping[str, int],
) -> NormalizerValidation:
    """Compare the benchmark normalizer with every supplied fixture row."""
    mismatches: list[NormalizerMismatch] = []
    for reference in references:
        actual = normalize_reference_ipa(
            reference.raw_ipa, language=language, vocab=vocab
        )
        actual_ids = (0, *(vocab[char] for char in actual), 0)
        reasons = []
        if actual != reference.expected_normalized:
            reasons.append("normalized text")
        if actual_ids != reference.expected_ids:
            reasons.append("token IDs")
        if reasons:
            mismatches.append(
                NormalizerMismatch(
                    reference.line_number,
                    reference.raw_ipa,
                    reference.expected_normalized,
                    actual,
                    reference.expected_ids,
                    actual_ids,
                    ", ".join(reasons),
                )
            )
    return NormalizerValidation(len(references), tuple(mismatches))


def extract_pronunciation(tokens: Sequence[GToken]) -> str:
    """Join lexical token phonemes while omitting punctuation phoneme tokens."""
    parts = [token.phonemes for token in tokens if token.is_word and token.phonemes]
    return canonicalize_actual(" ".join(parts))


def levenshtein(left: str, right: str) -> int:
    """Return edit distance using O(min(len(left), len(right))) memory."""
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, 1):
        current = [left_index]
        for right_index, right_char in enumerate(right, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def aggregate_results(
    language: str,
    results: Sequence[EntryResult],
    *,
    elapsed_seconds: float,
    normalizer_cases: int,
    normalizer_mismatches: int,
    worst_n: int,
) -> LanguageBenchmarkResult:
    entries = len(results)
    exact_matches = sum(result.exact_match for result in results)
    total_distance = sum(result.edit_distance for result in results)
    reference_characters = sum(result.reference_characters for result in results)
    cer = (
        total_distance / reference_characters
        if reference_characters
        else (0.0 if total_distance == 0 else 1.0)
    )
    mismatches = sorted(
        (result for result in results if not result.exact_match),
        key=lambda result: (-result.per_entry_cer, -result.edit_distance, result.word),
    )
    return LanguageBenchmarkResult(
        language=language,
        entries=entries,
        exact_matches=exact_matches,
        exact_match_rate=exact_matches / entries if entries else 0.0,
        total_edit_distance=total_distance,
        reference_characters=reference_characters,
        cer=cer,
        exceptions=sum(result.error is not None for result in results),
        elapsed_seconds=elapsed_seconds,
        words_per_second=entries / elapsed_seconds if elapsed_seconds else 0.0,
        normalizer_cases=normalizer_cases,
        normalizer_mismatches=normalizer_mismatches,
        worst_cases=tuple(mismatches[: max(0, worst_n)]),
    )


def create_benchmark_g2p(language: str) -> Any:
    """Create the documented deterministic G2P profile for one language."""
    if language == "en_US":
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(
            language="en-us",
            use_espeak_fallback=True,
            use_goruut_fallback=False,
            use_spacy=False,
            load_gold=True,
            load_silver=True,
            strict=True,
        )
    if language == "de_DE":
        from kokorog2p.de import GermanG2P

        return GermanG2P(
            language="de-de",
            use_espeak_fallback=True,
            use_goruut_fallback=False,
            use_spacy=False,
            use_lexicon=True,
            load_gold=True,
            load_silver=True,
            strip_stress=False,
        )
    raise ValueError(f"Unsupported Crane language: {language}")


def benchmark_language(
    *,
    config: CraneLanguageConfig,
    data_root: Path,
    limit: int | None,
    worst_n: int,
    fail_fast: bool = False,
    g2p: Any | None = None,
) -> LanguageBenchmarkResult:
    """Run one language after validating its external reference fixtures."""
    vocab = load_vocab(data_root / "g2p/kokoro_vocab.json")
    references = load_normalizer_ref(data_root / config.normalizer_ref_path)
    validation = validate_reference_normalizer(
        references, language=config.public_code, vocab=vocab
    )
    if validation.mismatches:
        raise CraneBenchmarkError(
            f"Crane reference normalizer is incompatible with supplied fixture: "
            f"language: {config.public_code}, cases: {validation.cases}, "
            f"mismatches: {validation.mismatch_count}"
        )
    entries = load_test_tsv(data_root / config.test_path)
    if limit is None and len(entries) != config.expected_entries:
        raise CraneBenchmarkError(
            f"{config.test_path}: expected {config.expected_entries} entries, "
            f"got {len(entries)}"
        )
    if limit is not None:
        entries = entries[:limit]
    converter = g2p or create_benchmark_g2p(config.public_code)
    started = time.perf_counter()
    results: list[EntryResult] = []
    for entry in entries:
        expected = normalize_reference_ipa(
            entry.expected_raw_ipa, language=config.public_code, vocab=vocab
        )
        try:
            actual = extract_pronunciation(converter(entry.word))
            error = None
        except Exception as exc:
            if fail_fast:
                raise CraneBenchmarkError(
                    f"{config.public_code}:{entry.line_number} {entry.word!r}: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            actual = ""
            error = f"{type(exc).__name__}: {exc}"
        results.append(
            EntryResult(
                entry.word,
                entry.expected_raw_ipa,
                expected,
                actual,
                levenshtein(expected, actual),
                len(expected),
                error is None and expected == actual,
                error,
            )
        )
    return aggregate_results(
        config.public_code,
        results,
        elapsed_seconds=time.perf_counter() - started,
        normalizer_cases=validation.cases,
        normalizer_mismatches=validation.mismatch_count,
        worst_n=worst_n,
    )


def _entry_to_dict(result: EntryResult) -> dict[str, Any]:
    value = asdict(result)
    value["per_entry_cer"] = result.per_entry_cer
    return value


def result_to_dict(
    result: LanguageBenchmarkResult,
    *,
    config: CraneLanguageConfig,
    profile: Mapping[str, Any],
) -> dict[str, Any]:
    """Serialize one language result using the stable JSON contract."""
    return {
        "dataset_file": config.test_path,
        "entries": result.entries,
        "profile": dict(profile),
        "normalizer_validation": {
            "file": config.normalizer_ref_path,
            "cases": result.normalizer_cases,
            "mismatches": result.normalizer_mismatches,
        },
        "metrics": {
            "cer": result.cer,
            "exact_match_rate": result.exact_match_rate,
            "exact_matches": result.exact_matches,
            "total_edit_distance": result.total_edit_distance,
            "reference_characters": result.reference_characters,
            "exceptions": result.exceptions,
            "elapsed_seconds": result.elapsed_seconds,
            "words_per_second": result.words_per_second,
        },
        "worst_cases": [_entry_to_dict(case) for case in result.worst_cases],
    }
