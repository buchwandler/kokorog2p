from __future__ import annotations

from benchmarks.reference.candidate import analyze_model_encoding


def test_valid_encoding_round_trips() -> None:
    result = analyze_model_encoding("hˈɛlO wˈɜɹld!")
    assert result.valid is True
    assert result.encoding_loss is False
    assert result.decoded == "hˈɛlO wˈɜɹld!"


def test_invalid_symbol_is_visible_and_lossy() -> None:
    result = analyze_model_encoding("hˈɛlO§")
    assert result.valid is False
    assert result.invalid_symbols == ("§",)
    assert result.encoding_loss is True


def test_spaces_and_punctuation_are_model_compatible() -> None:
    result = analyze_model_encoding("hˈɛlO, wˈɜɹld!")
    assert result.valid is True
    assert result.encoding_loss is False


def test_chinese_model_vocabulary_is_selected() -> None:
    result = analyze_model_encoding("ㄋㄧ2ㄏㄠ3", model="1.1")
    assert result.valid is True
    assert result.encoding_loss is False
