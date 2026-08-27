"""Network-free tests for the Crane benchmark infrastructure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from benchmarks import benchmark_crane_test_data as cli
from benchmarks.crane_test_data import (
    LANGUAGES,
    BenchmarkEntry,
    CraneBenchmarkError,
    EntryResult,
    NormalizerReference,
    aggregate_results,
    canonicalize_actual,
    create_benchmark_g2p,
    dataset_url,
    extract_pronunciation,
    levenshtein,
    load_normalizer_ref,
    load_test_tsv,
    normalize_reference_ipa,
    resolve_data_root,
    result_to_dict,
    validate_reference_normalizer,
)
from kokorog2p.token import GToken


def test_language_config_and_pinned_url() -> None:
    assert LANGUAGES["en_US"].hf_code == "en_us"
    assert LANGUAGES["en_US"].kokorog2p_code == "en-us"
    assert LANGUAGES["de_DE"].hf_code == "de_de"
    assert LANGUAGES["de_DE"].kokorog2p_code == "de-de"
    assert len(cli.CRANE_REVISION) == 40
    assert cli.CRANE_REVISION in dataset_url("g2p/en_us/test.tsv")
    assert "/main/" not in dataset_url("g2p/en_us/test.tsv")


def test_load_test_tsv_preserves_spelling_and_line_numbers(tmp_path: Path) -> None:
    path = tmp_path / "test.tsv"
    path.write_text(
        "apostrophe's\tɑ\n50-Franken-Noten\ta\nAstronomischen Kalender\ti\nҚазақ\tu\n"
    )
    entries = load_test_tsv(path)
    assert entries == [
        BenchmarkEntry("apostrophe's", "ɑ", 1),
        BenchmarkEntry("50-Franken-Noten", "a", 2),
        BenchmarkEntry("Astronomischen Kalender", "i", 3),
        BenchmarkEntry("Қазақ", "u", 4),
    ]


@pytest.mark.parametrize("content, fields", [("word", 1), ("word\tipa\textra", 3)])
def test_load_test_tsv_rejects_wrong_field_count(
    tmp_path: Path, content: str, fields: int
) -> None:
    path = tmp_path / "bad.tsv"
    path.write_text(content + "\n")
    with pytest.raises(
        ValueError, match=rf"{path}:1: expected 2 tab-separated fields, got {fields}"
    ):
        load_test_tsv(path)


def test_load_normalizer_ref_parses_empty_values_and_ids(tmp_path: Path) -> None:
    path = tmp_path / "normalizer.tsv"
    path.write_text("\t\t0,0\na\tb\t43,0\n")
    assert load_normalizer_ref(path) == [
        NormalizerReference("", "", (0, 0), 1),
        NormalizerReference("a", "b", (43, 0), 2),
    ]

    path.write_text("a\tb\tnot-an-int\n")
    with pytest.raises(ValueError, match="invalid comma-separated token IDs"):
        load_normalizer_ref(path)


def test_reference_normalization_covers_english_mapping_families() -> None:
    value = "t͡ʃ dʒ eɪ aɪ aʊ oʊ əʊ ɔɪ ɝ ɚ gab ́"
    chars = set("ʧʤAIWOQYɜɹəɹab ")
    vocab = {char: index for index, char in enumerate(chars)}
    assert normalize_reference_ipa(value, language="en_US", vocab=vocab) == (
        "ʧ ʤ A I W O Q Y ɜɹ əɹ ab"
    )


def test_reference_normalization_covers_german_mapping_families() -> None:
    value = "t͡s ts d͡z dz ss ʏ aʊ̯ aɪ̯ ɔʏ̯ n̩ l̩"
    chars = set("ʦʣSyaWIɔ ") | set("nql")
    vocab = {char: index for index, char in enumerate(chars)}
    assert normalize_reference_ipa(value, language="de_DE", vocab=vocab) == (
        "ʦ ʦ ʣ ʣ S y W I ɔy n l"
    )


def test_reference_normalizer_validation_checks_text_and_token_ids() -> None:
    vocab = {char: index for index, char in enumerate(" ab")}
    references = [NormalizerReference("  a  ", "a", (0, vocab["a"], 0), 1)]
    validation = validate_reference_normalizer(
        references, language="en_US", vocab=vocab
    )
    assert validation.cases == 1
    assert validation.mismatch_count == 0

    bad = [NormalizerReference("a", "b", (0, vocab["a"], 0), 2)]
    assert (
        validate_reference_normalizer(bad, language="en_US", vocab=vocab).mismatch_count
        == 1
    )


def test_whitespace_canonicalization() -> None:
    assert canonicalize_actual(" a\t b ") == "a b"
    assert canonicalize_actual(" a\u00a0b ") == "a b"
    assert canonicalize_actual(" a\nb ") == "a b"


def test_extract_pronunciation_omits_punctuation_and_keeps_order() -> None:
    tokens = [
        GToken("Anti", tag="NN", phonemes="an ti"),
        GToken("-", tag="-", phonemes="-"),
        GToken("Terror", tag="NN", phonemes="tɛɹə"),
        GToken(" ", tag="SPACE", phonemes=" "),
        GToken("", tag="NN", phonemes=""),
    ]
    assert extract_pronunciation(tokens) == "an ti tɛɹə"


def test_levenshtein_and_corpus_cer() -> None:
    assert levenshtein("", "") == 0
    assert levenshtein("abc", "abc") == 0
    assert levenshtein("abc", "ab") == 1
    assert levenshtein("ab", "abc") == 1
    assert levenshtein("abc", "axc") == 1
    results = [
        EntryResult("one", "a", "a", "", 1, 1, False, None),
        EntryResult("two", "abcdef", "abcdef", "abcdef", 0, 6, True, None),
    ]
    aggregate = aggregate_results(
        "en_US",
        results,
        elapsed_seconds=1.0,
        normalizer_cases=71,
        normalizer_mismatches=0,
        worst_n=20,
    )
    assert aggregate.cer == pytest.approx(1 / 7)
    assert aggregate.exact_match_rate == pytest.approx(1 / 2)
    assert aggregate.total_edit_distance == 1
    assert aggregate.reference_characters == 7


def test_exceptions_are_in_denominator_and_worst_sort_is_deterministic() -> None:
    results = [
        EntryResult("z", "ab", "ab", "", 2, 2, False, "RuntimeError: failed"),
        EntryResult("a", "abc", "abc", "ab", 1, 3, False, None),
    ]
    aggregate = aggregate_results(
        "en_US",
        results,
        elapsed_seconds=2.0,
        normalizer_cases=1,
        normalizer_mismatches=0,
        worst_n=1,
    )
    assert aggregate.exceptions == 1
    assert aggregate.worst_cases[0].word == "z"


def test_profile_construction_uses_documented_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import kokorog2p.de
    import kokorog2p.en

    class FakeG2P:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    monkeypatch.setattr(kokorog2p.en, "EnglishG2P", FakeG2P)
    english = create_benchmark_g2p("en_US")
    assert english.kwargs == {
        "language": "en-us",
        "use_espeak_fallback": True,
        "use_goruut_fallback": False,
        "use_spacy": False,
        "load_gold": True,
        "load_silver": True,
        "strict": True,
    }

    monkeypatch.setattr(kokorog2p.de, "GermanG2P", FakeG2P)
    german = create_benchmark_g2p("de_DE")
    assert german.kwargs["language"] == "de-de"
    assert german.kwargs["use_spacy"] is False
    assert german.kwargs["strip_stress"] is False


def test_missing_data_does_not_download_implicitly(tmp_path: Path) -> None:
    with pytest.raises(CraneBenchmarkError, match="Either:"):
        resolve_data_root(tmp_path, download=False, configs=[LANGUAGES["en_US"]])


def test_json_serialization_has_stable_content() -> None:
    config = LANGUAGES["en_US"]
    result = aggregate_results(
        "en_US",
        [],
        elapsed_seconds=0.0,
        normalizer_cases=71,
        normalizer_mismatches=0,
        worst_n=20,
    )
    value = result_to_dict(result, config=config, profile=cli.PROFILE_CONFIGS["en_US"])
    assert json.dumps(value, sort_keys=True) == json.dumps(value, sort_keys=True)
    assert value["metrics"]["cer"] == 0.0
    assert value["worst_cases"] == []


def test_cli_argument_contract() -> None:
    args = cli.parse_args(
        [
            "--language",
            "de_DE",
            "--data-root",
            "/tmp/data",
            "--download",
            "--cache-dir",
            "/tmp/cache",
            "--limit",
            "10",
            "--output",
            "/tmp/result.json",
            "--worst",
            "3",
            "--verbose",
            "--fail-fast",
        ]
    )
    assert args.language == "de_DE"
    assert args.limit == 10
    assert args.fail_fast is True
