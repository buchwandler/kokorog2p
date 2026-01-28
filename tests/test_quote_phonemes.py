"""Tests for configurable quote output in phonemes.

This test suite verifies that the phoneme_quotes parameter correctly controls
how quote characters appear in phoneme output.
"""

from typing import Literal

import pytest

from kokorog2p import get_g2p, phonemize_to_result


def phonemize_with_mode(
    mode: Literal["g2p", "pipeline"],
    text: str,
    *,
    language: str = "en-us",
    phoneme_quotes: str = "curly",
    use_spacy: bool | None = None,
) -> str:
    if use_spacy is None:
        g2p = get_g2p(language=language, phoneme_quotes=phoneme_quotes)
    else:
        g2p = get_g2p(
            language=language,
            phoneme_quotes=phoneme_quotes,
            use_spacy=use_spacy,
        )
    if mode == "g2p":
        return g2p.phonemize(text)
    return phonemize_to_result(text, g2p=g2p).phonemes or ""


@pytest.fixture(params=["g2p", "pipeline"])
def phoneme_backend(request: pytest.FixtureRequest) -> Literal["g2p", "pipeline"]:
    return request.param


class TestQuotePhonemes:
    """Test configurable quote output in phonemes."""

    def test_curly_quotes_default(self, phoneme_backend):
        """Test that curly quotes are used by default (backward compatible)."""
        result = phonemize_with_mode(phoneme_backend, 'Say "hi".', language="en-us")
        # Should contain curly quotes (U+201C, U+201D) by default
        assert "\u201c" in result or "\u201d" in result

    def test_curly_quotes_explicit(self, phoneme_backend):
        """Test explicit curly quotes setting."""
        result = phonemize_with_mode(
            phoneme_backend,
            'Say "hi".',
            language="en-us",
            phoneme_quotes="curly",
        )
        # Should contain curly quotes
        assert "\u201c" in result or "\u201d" in result

        result = phonemize_with_mode(
            phoneme_backend,
            "Say 'hi'.",
            language="en-us",
            phoneme_quotes="curly",
        )
        # Should contain curly quotes
        assert "\u201c" in result or "\u201d" in result

        result = phonemize_with_mode(
            phoneme_backend,
            "Say 'They'll like me'.",
            language="en-us",
            phoneme_quotes="curly",
        )
        # Should contain curly quotes
        assert "\u201c" in result or "\u201d" in result

        result = phonemize_with_mode(
            phoneme_backend,
            "Say They'll like me. I'm sure.",
            language="en-us",
            phoneme_quotes="curly",
        )
        # Should not contain curly quotes
        assert "\u201c" not in result and "\u201d" not in result

    def test_ascii_quotes(self, phoneme_backend):
        """Test ASCII quote output."""
        result = phonemize_with_mode(
            phoneme_backend,
            'Say "hi".',
            language="en-us",
            phoneme_quotes="ascii",
        )
        # Should contain ASCII quotes, not curly
        assert '"' in result
        assert "\u201c" not in result
        assert "\u201d" not in result

    def test_no_quotes(self, phoneme_backend):
        """Test quote removal."""
        result = phonemize_with_mode(
            phoneme_backend,
            'Say "hi".',
            language="en-us",
            phoneme_quotes="none",
        )
        # Should not contain any quote characters
        assert '"' not in result
        assert "\u201c" not in result
        assert "\u201d" not in result

    def test_original_bug_curly(self, phoneme_backend):
        """Test original bug report with curly quotes (default)."""
        result = phonemize_with_mode(
            phoneme_backend,
            'They replied, "we′re feel play".',
            language="en-us",
        )
        # Should have curly quotes by default
        assert "\u201c" in result or "\u201d" in result
        # And should have correct phonemes for we're
        assert "wɪɹ" in result

    def test_original_bug_ascii(self, phoneme_backend):
        """Test original bug report with ASCII quotes."""
        result = phonemize_with_mode(
            phoneme_backend,
            'They replied, "we′re feel play".',
            language="en-us",
            phoneme_quotes="ascii",
        )
        # Should have ASCII quotes
        assert '"' in result
        assert "\u201c" not in result and "\u201d" not in result
        # And should have correct phonemes for we're
        assert "wɪɹ" in result

    def test_original_bug_none(self, phoneme_backend):
        """Test original bug report with no quotes."""
        result = phonemize_with_mode(
            phoneme_backend,
            'They replied, "we′re feel play".',
            language="en-us",
            phoneme_quotes="none",
        )
        # Should not have any quotes
        assert '"' not in result
        assert "\u201c" not in result
        assert "\u201d" not in result
        # And should have correct phonemes for we're
        assert "wɪɹ" in result

    def test_nested_quotes_curly(self, phoneme_backend):
        """Test nested quotes with curly setting."""
        result = phonemize_with_mode(
            phoneme_backend,
            "She said, \"He said 'hello' to me\".",
            language="en-us",
            phoneme_quotes="curly",
        )
        # Should have curly quotes
        assert "\u201c" in result or "\u201d" in result

    def test_nested_quotes_ascii(self, phoneme_backend):
        """Test nested quotes with ASCII setting."""
        result = phonemize_with_mode(
            phoneme_backend,
            "She said, \"He said 'hello' to me\".",
            language="en-us",
            phoneme_quotes="ascii",
        )
        # Should have ASCII quotes
        assert '"' in result
        assert "\u201c" not in result and "\u201d" not in result

    def test_nested_quotes_none(self, phoneme_backend):
        """Test nested quotes with none setting."""
        result = phonemize_with_mode(
            phoneme_backend,
            "She said, \"He said 'hello' to me\".",
            language="en-us",
            phoneme_quotes="none",
        )
        # Should not have any quotes
        assert '"' not in result
        assert "\u201c" not in result
        assert "\u201d" not in result

    def test_other_punctuation_unaffected(self, phoneme_backend):
        """Test that other punctuation is not affected by phoneme_quotes."""
        text = "Hello, world! How are you?"
        result_curly = phonemize_with_mode(
            phoneme_backend, text, language="en-us", phoneme_quotes="curly"
        )
        result_ascii = phonemize_with_mode(
            phoneme_backend, text, language="en-us", phoneme_quotes="ascii"
        )
        result_none = phonemize_with_mode(
            phoneme_backend, text, language="en-us", phoneme_quotes="none"
        )

        # All should have same punctuation (comma, exclamation, question mark)
        for result in [result_curly, result_ascii, result_none]:
            assert "," in result
            assert "!" in result
            assert "?" in result


class TestQuotePhonemesCaching:
    """Test that caching respects different phoneme_quotes settings."""

    def test_cache_respects_setting(self):
        """Test that different phoneme_quotes settings use different cache entries."""
        # Create instances with different settings
        g2p_curly = get_g2p("en-us", phoneme_quotes="curly")
        g2p_ascii = get_g2p("en-us", phoneme_quotes="ascii")
        g2p_none = get_g2p("en-us", phoneme_quotes="none")

        text = 'Say "hi".'

        result_curly = g2p_curly.phonemize(text)
        result_ascii = g2p_ascii.phonemize(text)
        result_none = g2p_none.phonemize(text)

        # Results should be different
        assert result_curly != result_ascii
        assert result_ascii != result_none
        assert result_curly != result_none

    def test_cache_same_setting(self):
        """Test that same phoneme_quotes setting uses cached instance."""
        g2p1 = get_g2p("en-us", phoneme_quotes="ascii")
        g2p2 = get_g2p("en-us", phoneme_quotes="ascii")

        # Should be the same cached instance
        assert g2p1 is g2p2

    def test_cache_different_setting(self):
        """Test that different phoneme_quotes setting creates new instance."""
        g2p1 = get_g2p("en-us", phoneme_quotes="ascii")
        g2p2 = get_g2p("en-us", phoneme_quotes="curly")

        # Should be different instances
        assert g2p1 is not g2p2


class TestQuotePhonemesTokens:
    """Test quote handling at token level."""

    def test_token_text_unchanged(self):
        """Test that token.text still has curly quotes (for display)."""
        g2p = get_g2p("en-us", phoneme_quotes="ascii")
        tokens = g2p('Say "hi".')

        # token.text should still have curly quotes (for display purposes)
        quote_tokens = [t for t in tokens if t.text in ["\u201c", "\u201d", '"']]
        # Should have quote tokens (curly in text)
        assert len(quote_tokens) > 0

    def test_token_phonemes_respect_setting(self):
        """Test that token.phonemes respects phoneme_quotes setting."""
        g2p_ascii = get_g2p("en-us", phoneme_quotes="ascii")
        g2p_none = get_g2p("en-us", phoneme_quotes="none")

        tokens_ascii = g2p_ascii('Say "hi".')
        tokens_none = g2p_none('Say "hi".')

        # ASCII: Should have quote phonemes (ASCII)
        ascii_phonemes = "".join(t.phonemes for t in tokens_ascii if t.phonemes)
        assert '"' in ascii_phonemes

        # None: Should not have quote phonemes
        none_phonemes = "".join(t.phonemes for t in tokens_none if t.phonemes)
        assert '"' not in none_phonemes
        assert "\u201c" not in none_phonemes
        assert "\u201d" not in none_phonemes


class TestQuotePhonemesInvalidValues:
    """Test handling of invalid phoneme_quotes values."""

    def test_invalid_value_raises_error(self):
        """Test that invalid phoneme_quotes value raises ValueError."""
        with pytest.raises(ValueError, match="phoneme_quotes must be"):
            get_g2p("en-us", phoneme_quotes="invalid")

    def test_case_sensitive(self):
        """Test that phoneme_quotes is case-sensitive."""
        # These should raise errors (case mismatch)
        with pytest.raises(ValueError):
            get_g2p("en-us", phoneme_quotes="Curly")

        with pytest.raises(ValueError):
            get_g2p("en-us", phoneme_quotes="ASCII")

        with pytest.raises(ValueError):
            get_g2p("en-us", phoneme_quotes="None")


class TestQuotePhonemesWithSpacy:
    """Test quote handling with spaCy enabled/disabled."""

    def test_ascii_quotes_with_spacy(self, phoneme_backend):
        """Test ASCII quotes with spaCy enabled."""
        result = phonemize_with_mode(
            phoneme_backend,
            'Say "hi".',
            language="en-us",
            phoneme_quotes="ascii",
            use_spacy=True,
        )
        assert '"' in result
        assert "\u201c" not in result and "\u201d" not in result

    def test_ascii_quotes_without_spacy(self, phoneme_backend):
        """Test ASCII quotes without spaCy."""
        result = phonemize_with_mode(
            phoneme_backend,
            'Say "hi".',
            language="en-us",
            phoneme_quotes="ascii",
            use_spacy=False,
        )
        assert '"' in result
        assert "\u201c" not in result and "\u201d" not in result

    def test_none_quotes_with_spacy(self, phoneme_backend):
        """Test no quotes with spaCy enabled."""
        result = phonemize_with_mode(
            phoneme_backend,
            'Say "hi".',
            language="en-us",
            phoneme_quotes="none",
            use_spacy=True,
        )
        assert "\u201c" not in result and "\u201d" not in result
        assert "\u201c" not in result and "\u201d" not in result

    def test_none_quotes_without_spacy(self, phoneme_backend):
        """Test no quotes without spaCy."""
        result = phonemize_with_mode(
            phoneme_backend,
            'Say "hi".',
            language="en-us",
            phoneme_quotes="none",
            use_spacy=False,
        )
        assert "\u201c" not in result and "\u201d" not in result
        assert "\u201c" not in result and "\u201d" not in result
