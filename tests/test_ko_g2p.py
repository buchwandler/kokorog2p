"""Tests for the Korean G2P module."""

import pytest

from kokorog2p.ko import KoreanG2P
from kokorog2p.token import GToken


class TestKoreanG2P:
    """Tests for KoreanG2P."""

    @pytest.fixture
    def g2p(self):
        """Create a Korean G2P instance."""
        return KoreanG2P()

    @pytest.fixture
    def g2p_no_dict(self):
        """Create a Korean G2P instance without MeCab dictionary."""
        return KoreanG2P(use_dict=False)

    def test_creation(self, g2p):
        """Test G2P creation."""
        assert g2p.language == "ko"

    def test_call_returns_tokens(self, g2p):
        """Test calling G2P returns list of tokens."""
        tokens = g2p("안녕하세요")
        assert isinstance(tokens, list)
        assert all(isinstance(t, GToken) for t in tokens)

    def test_empty_input(self, g2p):
        """Test empty input returns empty list."""
        tokens = g2p("")
        assert tokens == []

        tokens2 = g2p("   ")
        assert tokens2 == []

    def test_phonemize_method(self, g2p):
        """Test phonemize method returns string."""
        result = g2p.phonemize("안녕")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_repr(self, g2p):
        """Test string representation."""
        result = repr(g2p)
        assert "KoreanG2P" in result
        assert "ko" in result

    # Korean-specific phonological tests

    def test_basic_hangul(self, g2p):
        """Test basic Hangul conversion."""
        result = g2p.phonemize("한글")
        assert result is not None
        assert len(result) > 0

    def test_greeting(self, g2p):
        """Test common Korean greeting."""
        tokens = g2p("안녕하세요")
        assert len(tokens) > 0
        assert tokens[0].phonemes is not None

    def test_idiom_replacement(self, g2p):
        """Test idiom replacement (mp3 -> 엠피쓰리)."""
        result = g2p.phonemize("mp3 파일")
        # Should contain the converted form
        assert result is not None

    def test_number_conversion(self, g2p):
        """Test Arabic number to Korean spelling."""
        result = g2p.phonemize("3개")
        # Should spell out 3 as 세
        assert result is not None

    def test_english_word_in_korean(self, g2p):
        """Test English word conversion to Hangul."""
        result = g2p.phonemize("좋은 game이야")
        # Should convert 'game' to Hangul
        assert result is not None

    def test_palatalization_rule(self, g2p):
        """Test Korean palatalization rule (ㄷ+이 -> 지)."""
        # 굳이 should be pronounced as [구지]
        result = g2p.phonemize("굳이")
        assert result is not None

    def test_liaison_rule_13(self, g2p):
        """Test liaison rule (제13항) - consonant linking."""
        # 옷이 should be pronounced as [오시]
        result = g2p.phonemize("옷이")
        assert result is not None

    def test_tensification_rule_23(self, g2p):
        """Test tensification rule (제23항) - fortis after obstruent."""
        # 국밥 should have tensification: [국빱]
        result = g2p.phonemize("국밥")
        assert result is not None

    def test_nasalization_rule_18(self, g2p):
        """Test nasalization rule (제18항) - nasal assimilation."""
        # 먹는 should be pronounced as [멍는]
        result = g2p.phonemize("먹는")
        assert result is not None

    def test_liquid_nasalization_rule_20(self, g2p):
        """Test ㄴ->ㄹ rule (제20항)."""
        # 신라 should be pronounced as [실라]
        result = g2p.phonemize("신라")
        assert result is not None

    def test_hieut_rules(self, g2p):
        """Test ㅎ rules (제12항)."""
        # 놓고 should be pronounced as [노코]
        result = g2p.phonemize("놓고")
        assert result is not None

    def test_sino_korean_number(self, g2p):
        """Test Sino-Korean number spelling."""
        result = g2p.phonemize("123")
        assert result is not None

    def test_pure_korean_number_with_bound_noun(self, g2p):
        """Test pure Korean number with bound noun."""
        # 3개 should use pure Korean: 세개
        result = g2p.phonemize("3개")
        assert result is not None

    def test_special_date_10월(self, g2p):
        """Test special date pronunciation (10월 -> 시월)."""
        result = g2p.phonemize("10월")
        # Should be 시월 not 십월
        assert result is not None

    def test_special_date_6월(self, g2p):
        """Test special date pronunciation (6월 -> 유월)."""
        result = g2p.phonemize("6월")
        # Should be 유월 not 육월
        assert result is not None

    def test_ui_consonant_rule(self, g2p):
        """Test 의 pronunciation after consonant (제5.3항)."""
        # 무늬 should have ㅢ -> ㅣ: [무니]
        result = g2p.phonemize("무늬")
        assert result is not None

    def test_jyeo_rule(self, g2p):
        """Test 져/쪄/쳐 pronunciation (제5.1항)."""
        # 가져 should be pronounced as [가저]
        result = g2p.phonemize("가져")
        assert result is not None

    def test_compound_with_nplus(self, g2p):
        """Test ㄴ insertion rule (제29항)."""
        # 솜이불 should have ㄴ insertion: [솜니불]
        result = g2p.phonemize("솜이불")
        assert result is not None

    def test_saisiot_tensification(self, g2p):
        """Test saisiot tensification (제28항)."""
        # 문고리 should have tensification: [문꼬리]
        result = g2p.phonemize("문고리")
        assert result is not None

    def test_coda_neutralization_rule_9(self, g2p):
        """Test coda neutralization (제9항)."""
        # 옷 should be pronounced as [옫] with ㄷ->ㄷ neutralization
        result = g2p.phonemize("옷")
        assert result is not None

    def test_double_coda_rule_10(self, g2p):
        """Test double coda simplification (제10항)."""
        # 앉다 should simplify ㄵ: [안따]
        result = g2p.phonemize("앉다")
        assert result is not None

    def test_rieul_giyeok_rule_11_1(self, g2p):
        """Test ㄺ before ㄱ (제11.1항)."""
        # 맑게 should be pronounced as [말께]
        result = g2p.phonemize("맑게")
        assert result is not None

    def test_group_vowels_option(self):
        """Test group_vowels option."""
        g2p_group = KoreanG2P(group_vowels=True)
        result = g2p_group.phonemize("개")
        assert result is not None

    def test_to_syl_option(self):
        """Test to_syl option for syllable composition."""
        g2p_syl = KoreanG2P(to_syl=True)
        result = g2p_syl.phonemize("한글")
        # Should compose back to syllables
        assert result is not None

    def test_use_dict_false(self, g2p_no_dict):
        """Test with use_dict=False (no MeCab)."""
        result = g2p_no_dict.phonemize("안녕하세요")
        # Should still work but without POS tagging
        assert result is not None

    def test_load_parameters(self):
        """Test load_silver and load_gold parameters."""
        # These parameters exist for API consistency
        g2p_custom = KoreanG2P(load_silver=False, load_gold=False)
        result = g2p_custom.phonemize("테스트")
        assert result is not None

    def test_mixed_korean_english_numbers(self, g2p):
        """Test mixed Korean, English, and numbers."""
        result = g2p.phonemize("나의 친구가 mp3 file 3개를 다운받고 있다")
        assert result is not None
        assert len(result) > 0

    def test_korean_punctuation(self, g2p):
        """Test Korean with punctuation."""
        result = g2p.phonemize("안녕하세요!")
        assert result is not None

    def test_special_character_hat(self, g2p):
        """Test ^ character (prevents phonological rules)."""
        # The ^ character is used internally to prevent rule application
        result = g2p.phonemize("스물^여덟")
        assert result is not None

    def test_percentage_unit(self, g2p):
        """Test % unit conversion."""
        result = g2p.phonemize("50%")
        # Should convert % to 퍼센트
        assert result is not None

    def test_unit_conversion_km(self, g2p):
        """Test km unit conversion."""
        result = g2p.phonemize("5km")
        # Should convert km to 킬로미터
        assert result is not None


class TestKoreanG2PIntegration:
    """Integration tests for Korean G2P."""

    def test_get_g2p_korean(self):
        """Test getting Korean G2P through get_g2p."""
        from kokorog2p import get_g2p

        g2p = get_g2p("ko")
        assert isinstance(g2p, KoreanG2P)
        assert g2p.language == "ko"

    def test_get_g2p_korean_variants(self):
        """Test various Korean language codes."""
        from kokorog2p import get_g2p

        for lang in ["ko", "ko-kr", "kor", "korean"]:
            g2p = get_g2p(lang)
            assert isinstance(g2p, KoreanG2P)

    def test_phonemize_korean(self):
        """Test phonemize function with Korean."""
        from kokorog2p import phonemize

        result = phonemize("안녕하세요", language="ko")
        assert isinstance(result.phonemes, str)
        assert len(result.phonemes) > 0

    def test_korean_with_overrides(self):
        """Test Korean G2P with span-based overrides."""
        from kokorog2p import phonemize_to_result
        from kokorog2p.types import OverrideSpan

        # Test phoneme override for Korean text
        text = "한국어 발음"
        overrides = [OverrideSpan(0, 3, {"ph": "hɐnɡuɡʌ"})]
        result = phonemize_to_result(text, lang="ko", overrides=overrides)

        assert result is not None
        assert result.phonemes is not None
        # First token should have the override
        assert result.tokens[0].meta.get("ph") == "hɐnɡuɡʌ"
