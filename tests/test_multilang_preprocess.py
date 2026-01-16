"""Tests for SSMD language preprocessing."""

import pytest

from kokorog2p.multilang import preprocess_multilang

pytest.importorskip("lingua")


class TestPreprocessMultilang:
    """Tests for preprocess_multilang."""

    def test_basic_language_annotation(self):
        text = "Schöne World"
        result = preprocess_multilang(
            text,
            markdown_syntax="ssmd",
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        assert result == '[Schöne]{lang="de"} World'
        result = preprocess_multilang(
            text,
            markdown_syntax="speechmarkdown",
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        assert result == '(Schöne)[lang:"de"] World'

    def test_preserves_existing_lang_annotation(self):
        text = '[Hallo]{lang="de"} World'
        result = preprocess_multilang(
            text,
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        assert result == text
        text = '(Hallo)[lang:"de"] World'
        result = preprocess_multilang(
            text,
            markdown_syntax="speechmarkdown",
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        assert result == text

    def test_preserves_phoneme_annotation(self):
        text = '[Bonjour]{ph="bɔ̃ʒuʁ"} World'
        result = preprocess_multilang(
            text,
            default_language="en-us",
            allowed_languages=["en-us", "fr"],
        )
        assert result == text
        text = '(Bonjour)[ipa:"bɔ̃ʒuʁ"] World'
        result = preprocess_multilang(
            text,
            markdown_syntax="speechmarkdown",
            default_language="en-us",
            allowed_languages=["en-us", "fr"],
        )
        assert result == text

    def test_keeps_punctuation(self):
        text = "Schöne, World!"
        result = preprocess_multilang(
            text,
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        assert result == '[Schöne]{lang="de"}, World!'
        result = preprocess_multilang(
            text,
            markdown_syntax="speechmarkdown",
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        assert result == '(Schöne)[lang:"de"], World!'

    def test_requires_default_language_in_allowed(self):
        with pytest.raises(ValueError):
            preprocess_multilang(
                "Schöne World",
                default_language="en-us",
                allowed_languages=["de"],
            )
        with pytest.raises(ValueError):
            preprocess_multilang(
                "Schöne World",
                markdown_syntax="speechmarkdown",
                default_language="en-us",
                allowed_languages=["de"],
            )
