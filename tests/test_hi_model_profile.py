"""Unit tests for the Hindi Kokoro model profile."""

import pytest

from kokorog2p.hi.model_profile import (
    HindiVocabularyError,
    model_profile_vocab,
    transform_hindi_ipa,
    validate_hindi_symbols,
)


def test_profile_preserves_hindi_phonetics() -> None:
    assert transform_hindi_ipa("nəmˈʌsteː dˈʊnɪjˌaː") == "nəmˈʌsteː dˈʊnɪjˌaː"
    assert transform_hindi_ipa("kɾˈɪpjˌaː dʰjˈaːn dˈẽː") == "kɾˈɪpjˌaː dʰjˈaːn dˈẽː"


def test_profile_preserves_non_english_distinctions() -> None:
    raw = "e eː aː ɾ ʋ ʰ ̃ ʈ ɖ ɳ ɽ ʂ ɟ q x ɣ"
    assert transform_hindi_ipa(raw) == raw


def test_profile_removes_only_unsupported_espeak_controls() -> None:
    assert transform_hindi_ipa("r\u0329ə") == "rə"
    assert transform_hindi_ipa("t͡ʃ") == "tʃ"
    assert transform_hindi_ipa("t^ʃ") == "tʃ"
    assert transform_hindi_ipa("(en)nəm") == "nəm"


def test_profile_validates_against_stock_model() -> None:
    assert validate_hindi_symbols("nəmˈʌsteː dˈʊnɪjˌaː") == []
    assert set(model_profile_vocab()) >= set("eːaːɾʋʰ̃ʈɖɳɽʂɟqxɣˈˌ")


def test_profile_reports_context_for_invalid_symbol() -> None:
    with pytest.raises(HindiVocabularyError) as error:
        validate_hindi_symbols("r§e", source_token="शब्द", raw_ipa="r§e")

    message = str(error.value)
    assert "§" in message
    assert "U+00A7" in message
    assert "शब्द" in message
    assert "r§e" in message
    assert "normalized='r§e'" in message


def test_profile_lenient_validation_returns_all_invalid_symbols() -> None:
    assert validate_hindi_symbols("§¤§", strict=False) == ["§", "¤", "§"]
