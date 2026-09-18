"""Test for CI bug where phonemize returns empty strings.

This test suite addresses the issue reported in PyKokoro where kokorog2p
was returning empty strings in CI environments due to silent exception
handling when espeak-ng failed to initialize.

GitHub issue: https://github.com/buchwandler/pykokoro
"""

import pytest

from kokorog2p import get_g2p


class TestEspeakEmptyStringBugFix:
    """Test that espeak backend never returns empty strings silently."""

    def test_espeak_phonemize_not_empty(self):
        """Espeak backend should never return empty strings for valid input.

        Regression test for CI bug where espeak initialization failures
        were silently caught and returned empty strings.
        """
        # This should either work OR raise an exception
        # It should NEVER return an empty string silently
        g2p = get_g2p(language="en-us", backend="espeak", lexicons=())

        # If we get here, initialization succeeded
        # Phonemization should work
        result = g2p.phonemize("test")

        assert len(result) > 0, (
            f"phonemize() returned empty string: [{result}]. "
            f"This indicates espeak-ng is not properly initialized."
        )
        assert result != "", "phonemize() should not return empty string"

    def test_dict_based_with_espeak_fallback(self):
        """Dictionary-based G2P with espeak fallback should work or fail clearly."""
        g2p = get_g2p(
            language="en-us",
            use_espeak_fallback=True,
            lexicons=(),
            backend="kokorog2p",
        )

        result = g2p.phonemize("test")

        # Should return valid phonemes
        assert len(result) > 0, (
            f"phonemize() returned empty string: [{result}]. "
            f"Dictionary-based G2P should work for common words."
        )
        assert result != ""

    def test_espeak_lookup_not_none(self):
        """Espeak lookup should return phonemes or raise error, not None."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="en-us")

        # lookup should return phonemes or raise an error
        # It should not silently return None
        result = g2p.lookup("test")

        assert result is not None, "lookup() should not return None for valid words"
        assert isinstance(result, str), "lookup() should return a string"
        assert len(result) > 0, "lookup() should not return empty string"

    def test_espeak_call_returns_tokens(self):
        """Espeak __call__ should return list of tokens with phonemes."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="en-us")

        # __call__ should return list of tokens
        tokens = g2p("test")

        assert isinstance(tokens, list), "__call__() should return a list"
        assert len(tokens) > 0, "__call__() should return at least one token"

        # Check first token has phonemes
        first_token = tokens[0]
        assert hasattr(first_token, "phonemes"), "Token should have phonemes attribute"
        assert first_token.phonemes is not None, "Token phonemes should not be None"


class TestGoruutEmptyStringBugFix:
    """Test that goruut backend never returns empty strings silently.

    These tests use an injected fake goruut process — they never download
    or start the real Goruut executable.
    """

    def test_goruut_phonemize_not_empty(self, monkeypatch: pytest.MonkeyPatch):
        """Goruut backend should never return empty strings for valid input."""

        from kokorog2p.backends.goruut import backend

        class FakeResult:
            def __str__(self):
                return "tˈɛst"

        class FakeGoruut:
            def phonemize(self, language, sentence, is_punct=True):
                return FakeResult()

        monkeypatch.setattr(backend, "_goruut_instance", FakeGoruut())
        try:
            g2p = get_g2p(language="en-us", backend="goruut", lexicons=())

            result = g2p.phonemize("test")

            assert len(result) > 0, (
                f"phonemize() returned empty string: [{result}]. "
                f"This indicates goruut is not properly initialized."
            )
            assert result != "", "phonemize() should not return empty string"
        finally:
            monkeypatch.setattr(backend, "_goruut_instance", None)

    def test_goruut_lookup_not_none(self, monkeypatch: pytest.MonkeyPatch):
        """Goruut lookup should return phonemes or raise error, not None."""
        from kokorog2p.backends.goruut import backend
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        class FakeResult:
            def __str__(self):
                return "tˈɛst"

        class FakeGoruut:
            def phonemize(self, language, sentence, is_punct=True):
                return FakeResult()

        monkeypatch.setattr(backend, "_goruut_instance", FakeGoruut())
        try:
            g2p = GoruutOnlyG2P(language="en-us")

            result = g2p.lookup("test")

            assert result is not None, "lookup() should not return None for valid words"
            assert isinstance(result, str), "lookup() should return a string"
            assert len(result) > 0, "lookup() should not return empty string"
        finally:
            monkeypatch.setattr(backend, "_goruut_instance", None)


class TestErrorHandling:
    """Test that initialization failures raise clear errors."""

    def test_espeak_with_invalid_voice_raises_error(self):
        """Invalid espeak voice should raise RuntimeError during first use."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        # Create instance with invalid voice
        g2p = EspeakOnlyG2P(language="xx-invalid-voice-12345")

        # Accessing espeak_backend should raise error during validation
        with pytest.raises(RuntimeError, match="Espeak backend"):
            _ = g2p.espeak_backend

    def test_espeak_phonemize_failure_raises_error(self):
        """If espeak somehow fails during phonemize, it should raise an error."""
        from unittest.mock import patch

        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="en-us")

        # Mock the backend to raise an exception
        with patch.object(g2p, "_espeak_backend") as mock_backend:
            mock_backend.phonemize.side_effect = RuntimeError("Test error")

            # Should re-raise with helpful message
            with pytest.raises(RuntimeError, match="EspeakOnlyG2P failed to phonemize"):
                g2p.phonemize("test")


class TestStrictParameter:
    """Test the strict parameter functionality."""

    def test_espeak_strict_true_raises_on_error(self):
        """With strict=True, espeak should raise errors."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="en-us", strict=True)

        # Mock the backend to raise an exception
        from unittest.mock import patch

        with patch.object(g2p, "_espeak_backend") as mock_backend:
            mock_backend.phonemize.side_effect = RuntimeError("Test error")

            # Should raise RuntimeError in strict mode
            with pytest.raises(RuntimeError, match="EspeakOnlyG2P failed to phonemize"):
                g2p.phonemize("test")

    def test_espeak_strict_false_returns_empty_string(self):
        """With strict=False, espeak should return empty string on error."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="en-us", strict=False)

        # Mock the backend to raise an exception
        from unittest.mock import patch

        with patch.object(g2p, "_espeak_backend") as mock_backend:
            mock_backend.phonemize.side_effect = RuntimeError("Test error")

            # Should return empty string in non-strict mode
            result = g2p.phonemize("test")
            assert result == "", "Should return empty string in non-strict mode"

    def test_get_g2p_strict_parameter(self):
        """get_g2p() should accept and pass through strict parameter."""
        # Test with strict=True (default)
        g2p_strict = get_g2p(
            language="en-us", backend="espeak", strict=True, lexicons=()
        )
        assert g2p_strict.strict is True, "strict should be True"

        # Test with strict=False
        g2p_lenient = get_g2p(
            language="en-us", backend="espeak", strict=False, lexicons=()
        )
        assert g2p_lenient.strict is False, "strict should be False"

    def test_goruut_strict_true_raises_on_error(self, monkeypatch: pytest.MonkeyPatch):
        """With strict=True, goruut should raise errors."""
        from kokorog2p.backends.goruut import backend
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        class FakeGoruut:
            def phonemize(self, language, sentence, is_punct=True):
                raise RuntimeError("Test error")

        monkeypatch.setattr(backend, "_goruut_instance", FakeGoruut())
        try:
            g2p = GoruutOnlyG2P(language="en-us", strict=True)

            # Should raise RuntimeError in strict mode
            with pytest.raises(RuntimeError, match="GoruutOnlyG2P failed to phonemize"):
                g2p.phonemize("test")
        finally:
            monkeypatch.setattr(backend, "_goruut_instance", None)

    def test_goruut_strict_false_returns_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """With strict=False, goruut should return empty string on error."""
        from kokorog2p.backends.goruut import backend
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        class FakeGoruut:
            def phonemize(self, language, sentence, is_punct=True):
                raise RuntimeError("Test error")

        monkeypatch.setattr(backend, "_goruut_instance", FakeGoruut())
        try:
            g2p = GoruutOnlyG2P(language="en-us", strict=False)

            # Should return empty string in non-strict mode
            result = g2p.phonemize("test")
            assert result == "", "Should return empty string in non-strict mode"
        finally:
            monkeypatch.setattr(backend, "_goruut_instance", None)

    def test_english_g2p_strict_parameter(self):
        """EnglishG2P should accept strict parameter."""
        from kokorog2p.en import EnglishG2P

        g2p_strict = EnglishG2P(language="en-us", lexicons=(), strict=True)
        assert g2p_strict.strict is True

        g2p_lenient = EnglishG2P(language="en-us", lexicons=(), strict=False)
        assert g2p_lenient.strict is False
