"""Regression tests for optional dependency loading and library silence."""

from types import SimpleNamespace

import pytest

from kokorog2p._optional import load_spacy_model


def test_spacy_model_loader_does_not_download(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_spacy = SimpleNamespace(
        util=SimpleNamespace(is_package=lambda _name: False),
    )
    monkeypatch.setitem(__import__("sys").modules, "spacy", fake_spacy)

    with pytest.raises(ImportError, match="python -m spacy download missing_model"):
        load_spacy_model("missing_model")


def test_korean_g2p_does_not_download_cmudict_at_import(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("jamo")
    from kokorog2p.ko.g2pk import G2p

    def fail_download(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("network download attempted")

    fake_nltk = SimpleNamespace(
        data=SimpleNamespace(find=lambda _name: (_ for _ in ()).throw(LookupError)),
        download=fail_download,
    )
    monkeypatch.setitem(__import__("sys").modules, "nltk", fake_nltk)

    # Construction only initializes local rule data; CMUdict is resolved lazily.
    g2p = G2p()
    assert g2p._cmu is None


def test_missing_cmudict_error_is_actionable(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("jamo")
    from kokorog2p.ko.g2pk import G2p

    fake_cmudict = SimpleNamespace(dict=lambda: (_ for _ in ()).throw(LookupError))
    fake_nltk_corpus = SimpleNamespace(cmudict=fake_cmudict)
    monkeypatch.setitem(__import__("sys").modules, "nltk.corpus", fake_nltk_corpus)

    g2p = G2p()
    with pytest.raises(LookupError, match="nltk.downloader cmudict"):
        _ = g2p.cmu


def test_convert_eng_is_silent(capsys: pytest.CaptureFixture[str]) -> None:
    pytest.importorskip("jamo")
    from kokorog2p.ko.english import convert_eng

    convert_eng("HELLO", {})
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
