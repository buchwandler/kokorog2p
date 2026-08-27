"""Unit tests for the Kazakh Kokoro model profile."""

import pytest

from kokorog2p.kk.model_profile import (
    KazakhVocabularyError,
    model_profile_vocab,
    transform_kazakh_ipa,
    validate_kazakh_symbols,
)


def test_profile_rewrites_generic_tied_phonemes() -> None:
    assert transform_kazakh_ipa("a^ɪ a^ʊ d^z d^ʒ e^ɪ o^ʊ ə^ʊ s^s t^s t^ʃ ɔ^ɪ") == (
        "I W ʣ ʤ A O Q S ʦ ʧ Y"
    )
    assert transform_kazakh_ipa("t͡ʃ") == "ʧ"


def test_profile_preserves_non_english_symbols() -> None:
    assert transform_kazakh_ipa("rxeqʁ") == "rxeqʁ"


def test_profile_validates_against_stock_model() -> None:
    assert validate_kazakh_symbols("rxeqʁ") == []
    assert set(model_profile_vocab()) >= set("rxeqʁ")


def test_profile_reports_context_for_invalid_symbol() -> None:
    with pytest.raises(KazakhVocabularyError) as error:
        validate_kazakh_symbols("r§e", source_token="сөз", raw_ipa="r§e")

    message = str(error.value)
    assert "§" in message
    assert "U+00A7" in message
    assert "сөз" in message
    assert "r§e" in message


def test_profile_lenient_validation_returns_all_invalid_symbols() -> None:
    assert validate_kazakh_symbols("§¤§", strict=False) == ["§", "¤", "§"]
