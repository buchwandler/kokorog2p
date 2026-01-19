"""Tests for language preprocessing."""

import pytest

from kokorog2p.multilang import preprocess_multilang
from kokorog2p.types import OverrideSpan

pytest.importorskip("lingua")


class TestPreprocessMultilang:
    """Tests for preprocess_multilang."""

    def test_basic_language_annotation(self):
        text = "Schöne World"
        result = preprocess_multilang(
            text,
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        # Should return list of OverrideSpan objects
        assert isinstance(result, list)
        assert len(result) == 1  # Only "Schöne" should be detected as German
        assert isinstance(result[0], OverrideSpan)
        assert result[0].char_start == 0
        assert result[0].char_end == 6  # len("Schöne")
        assert result[0].attrs == {"lang": "de"}

    def test_no_overrides_for_default_language(self):
        text = "Hello World"
        result = preprocess_multilang(
            text,
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        # Should return empty list (all words are in default language)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_multiple_language_switches(self):
        text = "Schöne World Guten Tag"
        result = preprocess_multilang(
            text,
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        # Should detect "Schöne" and "Guten" and "Tag" as German
        assert isinstance(result, list)
        assert len(result) >= 2  # At least "Schöne" and one of "Guten"/"Tag"
        # Check first override is "Schöne"
        assert result[0].char_start == 0
        assert result[0].char_end == 6
        assert result[0].attrs["lang"] == "de"

    def test_keeps_punctuation(self):
        text = "Schöne, World!"
        result = preprocess_multilang(
            text,
            default_language="en-us",
            allowed_languages=["en-us", "de"],
        )
        # Punctuation should not be in overrides
        assert isinstance(result, list)
        assert len(result) == 1
        # Only "Schöne" should have an override
        assert result[0].char_start == 0
        assert result[0].char_end == 6

    def test_requires_default_language_in_allowed(self):
        with pytest.raises(ValueError):
            preprocess_multilang(
                "Schöne World",
                default_language="en-us",
                allowed_languages=["de"],
            )
