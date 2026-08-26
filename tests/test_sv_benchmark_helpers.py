import importlib.util
import sys
from pathlib import Path

import pytest

from kokorog2p.sv import phonemize_word_raw

_MODULE_PATH = Path(__file__).parents[1] / "benchmarks" / "benchmark_sv_rules.py"
_SPEC = importlib.util.spec_from_file_location("benchmark_sv_rules", _MODULE_PATH)
assert _SPEC and _SPEC.loader
benchmark = importlib.util.module_from_spec(_SPEC)
sys.modules["benchmark_sv_rules"] = benchmark
_SPEC.loader.exec_module(benchmark)


def test_reference_parser_streams_space_separated_phones(tmp_path: Path) -> None:
    path = tmp_path / "lexicon.tsv"
    path.write_text("foo\tf uː\n\nbar\tb ɑː r\n", encoding="utf-8")
    cases = list(benchmark.iter_reference_cases(path))
    assert [(case.line_number, case.word, case.phones) for case in cases] == [
        (1, "foo", ("f", "uː")),
        (3, "bar", ("b", "ɑː", "r")),
    ]


def test_reference_parser_reports_malformed_rows(tmp_path: Path) -> None:
    path = tmp_path / "bad.tsv"
    path.write_text("missing-tab\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected word<TAB>ipa"):
        list(benchmark.iter_reference_cases(path))


def test_metrics_and_levenshtein_alignment() -> None:
    assert benchmark.without_stress(("ˈ", "aː")) == ("", "aː")
    assert benchmark.without_quantity(("ˈ", "aː")) == ("", "a")
    assert benchmark.levenshtein_counts(("a", "b"), ("a", "c", "d")) == (2, 1, 1, 0)
    assert benchmark.levenshtein_distance(("a",), ("a",)) == 0


def test_split_is_stable_and_distributed() -> None:
    assert benchmark.stable_split("hej") == benchmark.split_for_word("hej")
    assert {benchmark.split_for_word(str(index)) for index in range(100)} == {
        "train",
        "dev",
        "test",
    }


def test_benchmark_writes_reports_without_real_corpus(tmp_path: Path) -> None:
    rows = []
    for word in ("hej", "sjuk", "tak"):
        result = phonemize_word_raw(word)
        rows.append(f"{word}\t{' '.join(result.phones)}")
    lexicon = tmp_path / "lexicon.tsv"
    lexicon.write_text("\n".join(rows) + "\n", encoding="utf-8")
    output = tmp_path / "result"
    exit_code = benchmark.main(
        ["--lexicon", str(lexicon), "--output", str(output), "--trace-failures"]
    )
    assert exit_code == 0
    for name in (
        "summary.json",
        "failures.tsv",
        "groups.tsv",
        "confusions.tsv",
        "rule_coverage.tsv",
        "stress_failures.tsv",
        "quantity_failures.tsv",
        "prefixes.tsv",
        "suffixes.tsv",
        "ngrams.tsv",
        "regressions.tsv",
        "improvements.tsv",
    ):
        assert (output / name).exists(), name
    assert benchmark.main(["--lexicon", str(lexicon), "--inspect-format", "2"]) == 0
