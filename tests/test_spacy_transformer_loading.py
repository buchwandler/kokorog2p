"""Component-aware spaCy loader tests using small fake pipelines."""

from types import SimpleNamespace

import pytest

from kokorog2p._optional import load_spacy_model


class FakeNLP:
    def __init__(self, pipe_names: tuple[str, ...]) -> None:
        self.pipe_names = list(pipe_names)
        self.disabled: list[str] = []

    def disable_pipes(self, *names: str) -> None:
        self.disabled.extend(names)


def _fake_spacy(monkeypatch, nlp: FakeNLP):
    fake = SimpleNamespace(
        util=SimpleNamespace(is_package=lambda _name: True),
        load=lambda _name: nlp,
    )
    monkeypatch.setitem(__import__("sys").modules, "spacy", fake)


def test_transformer_and_tagger_pipeline_is_accepted(monkeypatch) -> None:
    nlp = FakeNLP(("transformer", "tagger", "parser", "ner"))
    _fake_spacy(monkeypatch, nlp)

    loaded = load_spacy_model("en_core_web_trf", enable=["tok2vec", "tagger"])

    assert loaded is nlp
    assert nlp.disabled == ["parser", "ner"]


def test_classic_tok2vec_and_tagger_pipeline_is_accepted(monkeypatch) -> None:
    nlp = FakeNLP(("tok2vec", "tagger", "ner"))
    _fake_spacy(monkeypatch, nlp)

    load_spacy_model("en_core_web_sm", enable=["tok2vec", "tagger"])

    assert nlp.disabled == ["ner"]


def test_missing_required_component_has_actionable_error(monkeypatch) -> None:
    nlp = FakeNLP(("transformer", "ner"))
    _fake_spacy(monkeypatch, nlp)

    with pytest.raises(ImportError, match="tagger"):
        load_spacy_model("en_core_web_trf", enable=["tok2vec", "tagger"])
