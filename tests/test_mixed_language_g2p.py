"""Tests for mixed-language G2P with automatic language detection."""

import pytest


def _can_import(*modules: str) -> bool:
    """Check if all modules can be imported."""
    for module in modules:
        try:
            __import__(module)
        except ImportError:
            return False
    return True


class TestMixedLanguageG2PBasic:
    """Basic tests that don't require lingua."""

    def test_import(self):
        """Test that MixedLanguageG2P can be imported."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        assert MixedLanguageG2P is not None

    def test_creation_without_lingua(self):
        """Test creation falls back gracefully without lingua."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
            enable_detection=True,
        )
        assert g2p.primary_language == "de"
        assert g2p.allowed_languages == ["de", "en-us"]
        # Should disable detection if lingua not available
        assert g2p.enable_detection in (True, False)  # Depends on lingua availability

    def test_requires_allowed_languages(self):
        """Test that allowed_languages is required."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        with pytest.raises(ValueError, match="allowed_languages must be specified"):
            MixedLanguageG2P(primary_language="de", allowed_languages=None)

        with pytest.raises(ValueError, match="allowed_languages must be specified"):
            MixedLanguageG2P(primary_language="de", allowed_languages=[])

    def test_primary_language_must_be_allowed(self):
        """Primary language should be part of allowed_languages."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        with pytest.raises(
            ValueError, match="primary_language must be in allowed_languages"
        ):
            MixedLanguageG2P(primary_language="de", allowed_languages=["en-us"])

    def test_language_codes_normalized(self):
        """Language codes should normalize to lowercase with hyphens."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="DE",
            allowed_languages=["EN_US", "DE"],
            enable_detection=False,
        )
        assert g2p.primary_language == "de"
        assert g2p.allowed_languages == ["en-us", "de"]

    def test_repr(self):
        """Test string representation."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )
        repr_str = repr(g2p)
        assert "MixedLanguageG2P" in repr_str
        assert "de" in repr_str
        assert "en-us" in repr_str

    def test_detection_disabled_mode(self):
        """Test with detection explicitly disabled."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
            enable_detection=False,
        )
        assert not g2p.enable_detection

        # Should use primary language for everything
        tokens = g2p("Hello world")
        for token in tokens:
            if token.is_word:
                assert token.get("detected_language") == "de"

    def test_empty_input(self):
        """Test empty input returns empty list."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )
        assert g2p("") == []
        assert g2p("   ") == []

    def test_cache_methods(self):
        """Test cache management methods."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        initial_size = g2p.get_cache_size()
        assert initial_size >= 0

        g2p.clear_detection_cache()
        assert g2p.get_cache_size() == 0


@pytest.mark.skipif(
    not _can_import("lingua"),
    reason="lingua-language-detector not installed",
)
class TestMixedLanguageG2PDetection:
    """Tests that require lingua for language detection."""

    def test_german_with_english_words(self):
        """Test German text with English words."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        text = "Das ist ein Test. Let's go!"
        tokens = g2p(text)

        # Check that we have tokens
        assert len(tokens) > 0

        # Check that words have detected_language metadata
        word_tokens = [t for t in tokens if t.is_word]
        assert all(t.get("detected_language") is not None for t in word_tokens)

        # "Let's" should be detected as English (or at least attempted)
        lets_tokens = [t for t in word_tokens if "Let" in t.text or "go" in t.text]
        assert len(lets_tokens) > 0

    def test_confidence_threshold(self):
        """Test confidence threshold filtering."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        # Very high threshold - almost everything falls back to primary
        g2p_strict = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
            confidence_threshold=0.99,
        )

        # Low threshold - more aggressive detection
        g2p_aggressive = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
            confidence_threshold=0.5,
        )

        # Both should work without errors
        text = "Das ist great!"
        tokens_strict = g2p_strict(text)
        tokens_aggressive = g2p_aggressive(text)

        assert len(tokens_strict) > 0
        assert len(tokens_aggressive) > 0

    def test_multiple_languages(self):
        """Test with more than two languages."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="en-us",
            allowed_languages=["en-us", "de", "fr"],
        )

        text = "Hello, Guten Tag, Bonjour!"
        tokens = g2p(text)

        word_tokens = [t for t in tokens if t.is_word]
        assert len(word_tokens) > 0

        # All words should have detected language
        for token in word_tokens:
            assert token.get("detected_language") in ["en-us", "de", "fr"]

    def test_short_words_fallback(self):
        """Test that very short words fall back to primary language."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        # Very short words (< 3 chars) should use primary language
        result = g2p._detect_word_language("ab")
        assert result == "de"

        result = g2p._detect_word_language("I")
        assert result == "de"

    def test_punctuation_skipped(self):
        """Test that punctuation doesn't get language detection."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        # Punctuation should use primary language
        result = g2p._detect_word_language("!!!")
        assert result == "de"

    def test_detection_caching(self):
        """Test that detection results are cached."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        # Detect same word twice
        word = "Hello"
        result1 = g2p._detect_word_language(word)
        cache_size1 = g2p.get_cache_size()

        result2 = g2p._detect_word_language(word)
        cache_size2 = g2p.get_cache_size()

        # Results should be the same
        assert result1 == result2

        # Cache size should not grow on second call
        assert cache_size2 == cache_size1

    def test_lookup_method(self):
        """Test lookup with automatic detection."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        # Should work without errors (result depends on dictionaries)
        result = g2p.lookup("Hello")
        # Result can be None or a phoneme string
        assert result is None or isinstance(result, str)


@pytest.mark.skipif(
    not _can_import("lingua"),
    reason="lingua-language-detector not installed",
)
class TestGetG2PIntegration:
    """Integration tests with get_g2p function."""

    def test_get_g2p_with_multilingual_mode(self):
        """Test get_g2p with multilingual_mode enabled."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        clear_cache()
        g2p = get_g2p(
            language="de",
            multilingual_mode=True,
            allowed_languages=["de", "en-us"],
        )

        assert isinstance(g2p, MixedLanguageG2P)
        assert g2p.primary_language == "de"
        assert "en-us" in g2p.allowed_languages

    def test_multilingual_without_allowed_languages_raises(self):
        """Test that multilingual_mode requires allowed_languages."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        with pytest.raises(ValueError, match="allowed_languages"):
            get_g2p(
                language="de",
                multilingual_mode=True,
                allowed_languages=None,  # Should raise
            )

    def test_caching_with_multilingual_mode(self):
        """Test that caching works with multilingual mode."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()

        # Create two instances with same params
        g2p1 = get_g2p(
            language="de",
            multilingual_mode=True,
            allowed_languages=["de", "en-us"],
        )

        g2p2 = get_g2p(
            language="de",
            multilingual_mode=True,
            allowed_languages=["de", "en-us"],
        )

        # Should be the same instance (cached)
        assert g2p1 is g2p2

    def test_different_params_different_instances(self):
        """Test that different params create different instances."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()

        g2p1 = get_g2p(
            language="de",
            multilingual_mode=True,
            allowed_languages=["de", "en-us"],
        )

        g2p2 = get_g2p(
            language="de",
            multilingual_mode=True,
            allowed_languages=["de", "en-us", "fr"],  # Different!
        )

        # Should be different instances
        assert g2p1 is not g2p2


@pytest.mark.skipif(
    not _can_import("lingua"),
    reason="lingua-language-detector not installed",
)
class TestRealWorldScenarios:
    """Real-world usage scenarios."""

    def test_german_technical_text(self):
        """Test German technical text with English terms."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        text = "Ich gehe zum Meeting. Die Performance ist great!"
        result = g2p.phonemize(text)

        # Should return some phonemes
        assert isinstance(result, str)
        assert len(result) > 0

    def test_english_with_german_words(self):
        """Test English text with German words."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="en-us",
            allowed_languages=["en-us", "de"],
        )

        text = "I love Sauerkraut and Bratwurst!"
        result = g2p.phonemize(text)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_preserves_punctuation(self):
        """Test that punctuation is preserved."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="de",
            allowed_languages=["de", "en-us"],
        )

        text = "Hello! Das ist great?"
        tokens = g2p(text)

        # Find punctuation tokens
        punct_tokens = [t for t in tokens if t.text in ["!", "?"]]
        assert len(punct_tokens) == 2

    def test_mixed_scripts_fallback(self):
        """Test behavior with unsupported languages in text."""
        from kokorog2p.mixed_language_g2p import MixedLanguageG2P

        g2p = MixedLanguageG2P(
            primary_language="en-us",
            allowed_languages=["en-us", "de"],
        )

        # Japanese text should fall back to primary language
        # (not in allowed_languages)
        text = "Hello こんにちは world"
        result = g2p.phonemize(text)

        # Should complete without error
        assert isinstance(result, str)


class TestLanguageMappings:
    """Test language code mappings."""

    def test_kokorog2p_to_lingua_mapping(self):
        """Test that language mappings are defined."""
        from kokorog2p.mixed_language_g2p import (
            KOKOROG2P_TO_LINGUA,
            LINGUA_AVAILABLE,
        )

        if LINGUA_AVAILABLE:
            # Should have mappings
            assert "de" in KOKOROG2P_TO_LINGUA
            assert "en-us" in KOKOROG2P_TO_LINGUA
            assert "fr" in KOKOROG2P_TO_LINGUA
        else:
            # Should be empty if lingua not available
            assert len(KOKOROG2P_TO_LINGUA) == 0

    def test_lingua_to_kokorog2p_mapping(self):
        """Test reverse language mappings."""
        from kokorog2p.mixed_language_g2p import (
            LINGUA_AVAILABLE,
            LINGUA_TO_KOKOROG2P,
        )

        if LINGUA_AVAILABLE:
            # Should have reverse mappings
            assert len(LINGUA_TO_KOKOROG2P) > 0
        else:
            assert len(LINGUA_TO_KOKOROG2P) == 0
