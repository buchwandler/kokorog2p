from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from kokorog2p import GToken

bench = importlib.import_module("benchmarks.benchmark_language_stations")
corpora = importlib.import_module("benchmarks.station_corpora")
aggregate = importlib.import_module("benchmarks.benchmark_all_stations")


def test_scaled_corpus_reaches_target_without_truncating_sentence() -> None:
    corpus = corpora.get_corpus("th", profile="scaled", target_chars=2000)
    assert corpus.input_chars >= 2000
    assert all(
        sentence in corpora.LANGUAGES["th"]["sentences"]
        for sentence in corpus.sentences
    )
    assert corpus.text == " ".join(corpus.sentences)


def test_scaled_corpus_is_deterministic() -> None:
    first = corpora.get_corpus("de", profile="scaled", target_chars=2000)
    second = corpora.get_corpus("de", profile="scaled", target_chars=2000)
    assert first == second


def test_every_language_can_build_scaled_corpus() -> None:
    for language in corpora.LANGUAGES:
        corpus = corpora.get_corpus(language, profile="scaled", target_chars=1000)
        assert corpus.input_chars >= 1000


def test_explicit_source_metadata_wins_over_rating() -> None:
    token = GToken("ไทย", phonemes="k", rating="5")
    token.set("source", "lexicon")
    assert bench._source_for_token(token, "th") == "lexicon"


def test_arbitrary_rating_is_not_a_source_bucket() -> None:
    token = GToken("word", phonemes="k", rating="random-rating")
    assert bench._source_for_token(token, "en-us") == "resolved"


def test_german_numeric_rating_compatibility_remains() -> None:
    token = GToken("Wort", phonemes="v", rating=5)
    assert bench._source_for_token(token, "de") == "lexicon"


def test_factory_probe_does_not_require_thai_engine_or_spacy_import() -> None:
    source = Path(bench.__file__).read_text(encoding="utf-8")
    assert "ThaiEngine" not in source
    assert "import spacy" not in source
    assert "kokorog2p.th" not in source


def test_lazy_state_walk_is_bounded_and_nested() -> None:
    class Phonemizer:
        pass

    class Backend:
        def __init__(self) -> None:
            self._phonemizer = None

        def lookup(self, text: str) -> str:
            return text

    class Frontend:
        def __init__(self) -> None:
            self._lexphon = Backend()

    state = bench._lazy_state(Frontend())
    assert state["_lexphon"] == "present:Backend"
    assert state["G2P._lexphon._phonemizer"] == "none"
    assert "G2P._lexphon._phonemizer.some_other_field" not in state


def test_factory_summary_exposes_distinct_metrics() -> None:
    result = {
        "status": "ok",
        "process_cold_ms": 10.0,
        "factory_construct_ms": 2.0,
        "factory_cache_hit_ms": 0.1,
        "direct_first_ms": 3.0,
        "direct_warm_ms": 1.0,
        "prepared_first_ms": 4.0,
        "prepared_warm_ms": 2.0,
        "factory_object_reused": True,
        "output_equal": True,
    }
    summary = bench._factory_summary([result])
    assert summary["factory_construct_ms"] == 2.0
    assert summary["process_cold_ms"] == 10.0
    assert summary["factory_cache_hit_ms"] == 0.1
    assert summary["direct_first_ms"] == 3.0
    assert summary["prepared_warm_ms"] == 2.0


def test_failure_json_is_written_for_runtime_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_once(*args: object, **kwargs: object) -> None:
        context = args[6]
        context.update(
            "direct/frontend", run_index=1, sentence_index=2, input_text="bad input"
        )
        raise ValueError("bad benchmark input")

    monkeypatch.setattr(bench, "_run_once", fail_once)
    report = tmp_path / "failure.json"
    code = bench.main(
        ["--language", "en-us", "--fallback", "off", "--json", str(report)]
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert code == 1
    assert payload["status"] == "failed"
    assert payload["phase"] == "direct/frontend"
    assert payload["sentence_index"] == 2
    assert payload["error"] == {"type": "ValueError", "message": "bad benchmark input"}


def test_aggregate_preserves_child_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = {
        "schema_version": 2,
        "status": "failed",
        "language": "vi",
        "phase": "direct/frontend",
        "sentence_index": 3,
        "error": {"type": "ValueError", "message": "unsupported token"},
        "factory_summary": {"status": "ok", "factory_construct_ms": 1.0},
    }

    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        json_path = Path(command[command.index("--json") + 1])
        json_path.write_text(json.dumps(report), encoding="utf-8")
        return SimpleNamespace(
            returncode=1, stdout="child output\n", stderr="child error\n"
        )

    monkeypatch.setattr(aggregate.subprocess, "run", fake_run)
    output = tmp_path / "aggregate.json"
    assert (
        aggregate.main(["--language", "vi", "--keep-going", "--json", str(output)]) == 1
    )
    captured = capsys.readouterr()
    assert "direct/frontend sentence=3" in captured.out
    assert "ValueError: unsupported token" in captured.out
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["languages"]["vi"]["error"]["message"] == "unsupported token"
    assert payload["factory_matrix"]["vi"]["factory_construct_ms"] == 1.0


def test_aggregate_keeps_child_output_when_no_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_run(command: list[str], **kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(
            returncode=1, stdout="stdout tail", stderr="stderr detail"
        )

    monkeypatch.setattr(aggregate.subprocess, "run", fake_run)
    output = tmp_path / "aggregate.json"
    assert aggregate.main(["--language", "en-us", "--json", str(output)]) == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    child = payload["languages"]["en-us"]
    assert child["phase"] == "child/startup"
    assert child["stdout_tail"] == "stdout tail"
    assert child["stderr"] == "stderr detail"
