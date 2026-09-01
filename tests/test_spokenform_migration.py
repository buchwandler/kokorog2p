"""Tests for explicit Spokenform-to-KokoroG2P composition."""

import pytest

from kokorog2p import phonemize_prepared
from kokorog2p.pipeline_api import _spokenform_replacements_for_run


def _prepare(text: str, language: str):
    from spokenform import PreparationConfig, prepare_for_kokorog2p

    return prepare_for_kokorog2p(
        text,
        language=language,
        config=PreparationConfig.for_kokorog2p(language),
    )


def test_spokenform_is_an_explicit_preparation_step() -> None:
    source = "I have 2 kg."
    prepared = _prepare(source, "en")
    assert prepared.spoken_text != source

    result = phonemize_prepared(prepared.spoken_text, language="en-us", use_spacy=False)
    assert result.clean_text == prepared.spoken_text
    assert result.phonemes


def test_core_prepared_path_does_not_call_spokenform(monkeypatch) -> None:
    from kokorog2p import pipeline_api

    def forbidden(*_args, **_kwargs):
        raise AssertionError("Spokenform must not be called by prepared core")

    monkeypatch.setattr(pipeline_api, "_spokenform_replacements_for_run", forbidden)
    result = phonemize_prepared("Professor Klein wartet 2 Minuten.", language="de")
    assert result.clean_text == "Professor Klein wartet 2 Minuten."


def test_optional_adapter_preserves_source_coordinates() -> None:
    source = "Kosten: 2 kg."
    replacements = _spokenform_replacements_for_run(source, "de", source_offset=10)
    assert replacements
    for replacement in replacements:
        assert source[replacement.start - 10 : replacement.end - 10]
        assert replacement.start >= 10
        assert replacement.end <= 10 + len(source)


@pytest.mark.parametrize("language", ["en", "de", "fr", "es", "it", "pt", "cs"])
def test_optional_adapter_supports_migrated_languages(language: str) -> None:
    replacements = _spokenform_replacements_for_run("2 kg", language)
    assert replacements
    assert all(item.start == 0 and item.end == 4 for item in replacements)


def test_adapter_supports_protected_ranges() -> None:
    assert (
        _spokenform_replacements_for_run("1,5 kg", "de", protected_spans=((0, 6),))
        == []
    )
