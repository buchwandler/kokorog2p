"""Tests for multi-language G2P support (Chinese, Japanese, EspeakOnly).

These tests use pytest markers to skip when optional dependencies
are not available.
"""

import pytest

# =============================================================================
# Helper Functions
# =============================================================================


def _can_import(*modules: str) -> bool:
    """Check if all modules can be imported."""
    for module in modules:
        try:
            __import__(module)
        except ImportError:
            return False
    return True


# =============================================================================
# EspeakOnlyG2P Tests
# =============================================================================


class TestEspeakOnlyG2P:
    """Tests for EspeakOnlyG2P fallback class."""

    def test_creation(self):
        """Test basic creation."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="fr-fr")
        assert g2p.language == "fr-fr"
        assert g2p._espeak_voice == "fr-fr"

    def test_voice_mapping(self):
        """Test language to espeak voice mapping."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        # Direct mappings
        assert EspeakOnlyG2P("fr")._espeak_voice == "fr-fr"
        assert EspeakOnlyG2P("de")._espeak_voice == "de"
        assert EspeakOnlyG2P("es-es")._espeak_voice == "es"
        assert EspeakOnlyG2P("pt-br")._espeak_voice == "pt-br"

        # Base language fallback
        assert EspeakOnlyG2P("fr-ca")._espeak_voice == "fr-fr"

    def test_repr(self):
        """Test string representation."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="de-de")
        assert "EspeakOnlyG2P" in repr(g2p)
        assert "de-de" in repr(g2p)

    @pytest.mark.espeak
    def test_phonemize_french(self):
        """Test French phonemization with espeak."""
        pytest.importorskip("espeakng_loader")
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="fr-fr")
        result = g2p.phonemize("Bonjour")
        assert result  # Should return some phonemes
        assert isinstance(result, str)

    @pytest.mark.espeak
    def test_call_returns_tokens(self):
        """Test that calling returns GToken list."""
        pytest.importorskip("espeakng_loader")
        from kokorog2p.espeak_g2p import EspeakOnlyG2P
        from kokorog2p.token import GToken

        g2p = EspeakOnlyG2P(language="fr-fr")
        tokens = g2p("Bonjour le monde")
        assert isinstance(tokens, list)
        assert all(isinstance(t, GToken) for t in tokens)

    def test_empty_input(self):
        """Test empty input returns empty list."""
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        g2p = EspeakOnlyG2P(language="fr-fr")
        assert g2p("") == []
        assert g2p("   ") == []


class TestGetG2PFallback:
    """Tests for get_g2p fallback behavior."""

    def test_unknown_language_uses_fallback(self):
        """Test that unknown languages use EspeakOnlyG2P."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        clear_cache()
        g2p = get_g2p("sw-sw", backend="espeak")  # Swahili - not yet implemented
        assert isinstance(g2p, EspeakOnlyG2P)

    def test_french_uses_french_g2p(self):
        """Test French uses FrenchG2P."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.fr import FrenchG2P

        clear_cache()
        g2p = get_g2p("fr")
        assert isinstance(g2p, FrenchG2P)

    def test_czech_uses_czech_g2p(self):
        """Test Czech uses CzechG2P."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.cs import CzechG2P

        clear_cache()
        g2p = get_g2p("cs")
        assert isinstance(g2p, CzechG2P)

    def test_german_uses_german_g2p(self):
        """Test German uses GermanG2P."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.de import GermanG2P

        clear_cache()
        g2p = get_g2p("de")
        assert isinstance(g2p, GermanG2P)


# =============================================================================
# Chinese G2P Tests
# =============================================================================


class TestChineseG2P:
    """Tests for Chinese G2P."""

    def test_import(self):
        """Test that ChineseG2P can be imported."""
        from kokorog2p.zh import ChineseG2P

        assert ChineseG2P is not None

    def test_creation(self):
        """Test basic creation without dependencies."""
        from kokorog2p.zh import ChineseG2P

        g2p = ChineseG2P(language="zh")
        assert g2p.language == "zh"
        assert g2p.version == "1.1"

    def test_repr(self):
        """Test string representation."""
        from kokorog2p.zh import ChineseG2P

        g2p = ChineseG2P(language="zh-cn")
        assert "ChineseG2P" in repr(g2p)
        assert "zh-cn" in repr(g2p)

    def test_punctuation_mapping(self):
        """Test Chinese punctuation mapping."""
        from kokorog2p.zh import ChineseG2P

        result = ChineseG2P.map_punctuation("你好，世界！")
        assert "," in result
        assert "!" in result
        assert "，" not in result
        assert "！" not in result

    def test_retone(self):
        """Test tone marker conversion."""
        from kokorog2p.zh import ChineseG2P

        # First tone
        assert "→" in ChineseG2P.retone("ma˥")
        # Second tone
        assert "↗" in ChineseG2P.retone("ma˧˥")
        # Third tone
        assert "↓" in ChineseG2P.retone("ma˧˩˧")
        # Fourth tone
        assert "↘" in ChineseG2P.retone("ma˥˩")

    @pytest.mark.skipif(
        not _can_import("jieba", "pypinyin", "cn2an"),
        reason="Chinese dependencies not installed",
    )
    def test_phonemize(self):
        """Test Chinese phonemization."""
        from kokorog2p.zh import ChineseG2P

        g2p = ChineseG2P()
        result = g2p.phonemize("你好")
        assert result  # Should return some phonemes
        assert isinstance(result, str)

    @pytest.mark.skipif(
        not _can_import("jieba", "pypinyin", "cn2an"),
        reason="Chinese dependencies not installed",
    )
    def test_call_returns_tokens(self):
        """Test that calling returns GToken list."""
        from kokorog2p.token import GToken
        from kokorog2p.zh import ChineseG2P

        g2p = ChineseG2P()
        tokens = g2p("你好世界")
        assert isinstance(tokens, list)
        assert all(isinstance(t, GToken) for t in tokens)

    def test_empty_input(self):
        """Test empty input returns empty list."""
        from kokorog2p.zh import ChineseG2P

        g2p = ChineseG2P()
        assert g2p("") == []
        assert g2p("   ") == []

    def test_get_g2p_chinese(self):
        """Test get_g2p returns ChineseG2P for Chinese."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.zh import ChineseG2P

        clear_cache()
        g2p = get_g2p("zh")
        assert isinstance(g2p, ChineseG2P)

        clear_cache()
        g2p = get_g2p("zh-cn")
        assert isinstance(g2p, ChineseG2P)

        clear_cache()
        g2p = get_g2p("chinese")
        assert isinstance(g2p, ChineseG2P)

    def test_chinese_v11_validation(self):
        """Test that Chinese v1.1 output validates against v1.1-zh model."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.vocab import validate_for_kokoro

        # Test version 1.1 (Zhuyin output)
        clear_cache()
        g2p_11 = get_g2p("zh", version="1.1")
        result = g2p_11.phonemize("你好")

        # Should be invalid for base model
        is_valid_base, _ = validate_for_kokoro(result, model="1.0")
        assert not is_valid_base, "Zhuyin should be invalid for base model"

        # Should be valid for v1.1-zh model
        is_valid_v11, invalid = validate_for_kokoro(result, model="1.1")
        assert (
            is_valid_v11
        ), f"Zhuyin should be valid for 1.1 model. Invalid: {set(invalid)}"

        # Test legacy version (IPA output)
        clear_cache()
        g2p_legacy = get_g2p("zh", version="1.0")
        result_legacy = g2p_legacy.phonemize("你好")

        # Should be valid for base model
        is_valid_legacy, invalid_legacy = validate_for_kokoro(
            result_legacy, model="1.0"
        )
        assert (
            is_valid_legacy
        ), f"IPA should be valid for base model. Invalid: {set(invalid_legacy)}"

    def test_chinese_get_target_model(self):
        """Test that ChineseG2P reports correct target model."""
        from kokorog2p.zh import ChineseG2P

        g2p_11 = ChineseG2P(version="1.1")
        assert g2p_11.get_target_model() == "1.1"

        g2p_legacy = ChineseG2P(version="1.0")
        assert g2p_legacy.get_target_model() == "1.0"


# =============================================================================
# Japanese G2P Tests
# =============================================================================


class TestJapaneseG2P:
    """Tests for Japanese G2P."""

    def test_import(self):
        """Test that JapaneseG2P can be imported."""
        from kokorog2p.ja import JapaneseG2P

        assert JapaneseG2P is not None

    def test_creation(self):
        """Test basic creation without dependencies."""
        from kokorog2p.ja import JapaneseG2P

        g2p = JapaneseG2P(language="ja")
        assert g2p.language == "ja"
        assert g2p.backend == "pyopenjtalk"

    def test_repr(self):
        """Test string representation."""
        from kokorog2p.ja import JapaneseG2P

        g2p = JapaneseG2P(language="ja-jp")
        assert "JapaneseG2P" in repr(g2p)
        assert "ja-jp" in repr(g2p)

    def test_pron2moras(self):
        """Test pronunciation to mora conversion."""
        from kokorog2p.ja import JapaneseG2P

        # Simple test
        moras = JapaneseG2P.pron2moras("コンニチハ")
        assert isinstance(moras, list)
        assert len(moras) > 0

    @pytest.mark.skipif(
        not _can_import("pyopenjtalk"),
        reason="pyopenjtalk not installed",
    )
    def test_phonemize(self):
        """Test Japanese phonemization."""
        from kokorog2p.ja import JapaneseG2P

        g2p = JapaneseG2P()
        result = g2p.phonemize("こんにちは")
        assert result  # Should return some phonemes
        assert isinstance(result, str)

    @pytest.mark.skipif(
        not _can_import("pyopenjtalk"),
        reason="pyopenjtalk not installed",
    )
    def test_call_returns_tokens(self):
        """Test that calling returns GToken list."""
        from kokorog2p.ja import JapaneseG2P
        from kokorog2p.token import GToken

        g2p = JapaneseG2P()
        tokens = g2p("こんにちは世界")
        assert isinstance(tokens, list)
        assert all(isinstance(t, GToken) for t in tokens)

    def test_empty_input(self):
        """Test empty input returns empty list."""
        from kokorog2p.ja import JapaneseG2P

        g2p = JapaneseG2P()
        assert g2p("") == []
        assert g2p("   ") == []

    def test_get_g2p_japanese(self):
        """Test get_g2p returns JapaneseG2P for Japanese."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.ja import JapaneseG2P

        clear_cache()
        g2p = get_g2p("ja")
        assert isinstance(g2p, JapaneseG2P)

        clear_cache()
        g2p = get_g2p("ja-jp")
        assert isinstance(g2p, JapaneseG2P)

        clear_cache()
        g2p = get_g2p("japanese")
        assert isinstance(g2p, JapaneseG2P)
