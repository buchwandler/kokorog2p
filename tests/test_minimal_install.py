"""Smoke tests for the core package without spaCy or local models."""

import pytest

from kokorog2p import SpacyModelResolutionError, get_g2p, phonemize


def _missing_model(*_args, **_kwargs):
    raise SpacyModelResolutionError(
        "no local model",
        language="en",
        automatic=True,
        candidates=(),
        errors=(),
        spacy_available=False,
    )


def test_core_phonemize_works_without_spacy_model(monkeypatch):
    monkeypatch.setattr("kokorog2p.resolve_spacy_model", _missing_model)

    result = phonemize(
        "Hello",
        use_spacy=None,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
    )

    assert result.clean_text == "Hello"
    assert result.tokens


def test_core_explicit_spacy_requirement_is_strict(monkeypatch):
    monkeypatch.setattr("kokorog2p.resolve_spacy_model", _missing_model)

    with pytest.raises(SpacyModelResolutionError):
        get_g2p(
            "en-us",
            use_spacy=True,
            load_gold=False,
            load_silver=False,
            use_espeak_fallback=False,
        )


def test_kazakh_frontend_imports_without_loading_espeak() -> None:
    from kokorog2p.kk import KazakhG2P

    g2p = get_g2p("kk")
    assert isinstance(g2p, KazakhG2P)
    assert g2p._espeak_backend is None
