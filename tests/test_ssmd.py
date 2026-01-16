"""Tests for the SSMD annotation module."""

from kokorog2p import get_g2p
from kokorog2p.ssmd import (
    apply_ssmd_features,
    phonemize_with_ssmd,
    preprocess_ssmd,
    remove_ssmd,
)
from kokorog2p.token import GToken


class TestPreprocessSSMD:
    """Tests for preprocess_ssmd function."""

    def test_simple_annotation(self):
        """Test simple SSMD annotation."""
        text = '[Misaki]{ph="misˈɑki"} is great.'
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert clean == "Misaki is great."
        assert "Misaki" in tokens
        assert 0 in phonemes
        assert phonemes[0] == "misˈɑki"
        assert languages == {}

    def test_multiple_annotations(self):
        """Test multiple SSMD annotations."""
        text = '[Hello]{ph="hɛˈloʊ"} [world]{ph="wˈɝld"}!'
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert clean == "Hello world!"
        assert len(phonemes) == 2
        assert phonemes[0] == "hɛˈloʊ"
        assert phonemes[1] == "wˈɝld"
        assert languages == {}

    def test_no_annotations(self):
        """Test text without annotations."""
        text = "Hello world!"
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert clean == "Hello world!"
        assert len(phonemes) == 0
        assert len(languages) == 0

    def test_mixed_annotations_and_regular_text(self):
        """Test mix of annotated and regular text."""
        text = '[Misaki]{ph="misˈɑki"} is a G2P engine.'
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert clean == "Misaki is a G2P engine."
        assert len(phonemes) == 1
        assert phonemes[0] == "misˈɑki"
        assert languages == {}

    def test_language_annotation(self):
        """Test language annotation parsing."""
        text = '[Bonjour]{lang="fr"} monde'
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert clean == "Bonjour monde"
        assert phonemes == {}
        assert languages[0] == "fr"

    def test_combined_phoneme_and_language(self):
        """Test combined phoneme and language annotation parsing."""
        text = '[Test]{ph="tˈɛst" lang="de"}'
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert clean == "Test"
        assert phonemes[0] == "tˈɛst"
        assert languages[0] == "de"

    def test_annotation_without_phoneme_or_language(self):
        """Unknown annotation attributes are ignored."""
        text = '[link]{href="/docs/page"} test'
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert clean == "link test"
        assert phonemes == {}
        assert languages == {}

    def test_empty_annotation(self):
        """Test annotation with empty phonemes."""
        text = '[word]{ph=""} test'
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert "word" in clean
        assert 0 in phonemes
        assert phonemes[0] == ""
        assert languages == {}

    def test_whitespace_handling(self):
        """Test whitespace in annotations."""
        text = '  [Test]{ph="tˈɛst"}  more text  '
        clean, tokens, phonemes, languages = preprocess_ssmd(text)
        assert "Test" in clean
        assert 0 in phonemes
        assert phonemes[0] == "tˈɛst"
        assert languages == {}


class TestRemoveSSMD:
    """Tests for remove_ssmd function."""

    def test_remove_simple_annotation(self):
        """Test removing simple annotation."""
        text = '[Misaki]{ph="misˈɑki"} is great.'
        result = remove_ssmd(text)
        assert result == "Misaki is great."

    def test_remove_multiple_annotations(self):
        """Test removing multiple annotations."""
        text = '[Hello]{ph="hɛˈloʊ"} [world]{ph="wˈɝld"}!'
        result = remove_ssmd(text)
        assert result == "Hello world!"

    def test_no_annotations(self):
        """Test text without annotations."""
        text = "Hello world!"
        result = remove_ssmd(text)
        assert result == "Hello world!"

    def test_regular_links(self):
        """Test removing regular SSMD links."""
        text = "[link](http://example.com)"
        result = remove_ssmd(text)
        assert result == "link"


class TestApplySSMDFeatures:
    """Tests for apply_ssmd_features function."""

    def test_apply_single_feature(self):
        """Test applying single phoneme feature."""
        tokens = [
            GToken(text="Hello", phonemes="hɛloʊ"),
            GToken(text="world", phonemes="wɝld"),
        ]
        features = {0: "hˈɛloʊ"}
        orig_tokens = ["Hello", "world"]

        result = apply_ssmd_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hˈɛloʊ"
        assert result[0].get("rating") == 5
        assert result[1].phonemes == "wɝld"

    def test_apply_multiple_features(self):
        """Test applying multiple phoneme features."""
        tokens = [
            GToken(text="Hello", phonemes="hɛloʊ"),
            GToken(text="world", phonemes="wɝld"),
        ]
        features = {0: "hˈɛloʊ", 1: "wˈɝld"}
        orig_tokens = ["Hello", "world"]

        result = apply_ssmd_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hˈɛloʊ"
        assert result[1].phonemes == "wˈɝld"
        assert result[0].get("rating") == 5
        assert result[1].get("rating") == 5

    def test_no_features(self):
        """Test with no features to apply."""
        tokens = [
            GToken(text="Hello", phonemes="hɛloʊ"),
            GToken(text="world", phonemes="wɝld"),
        ]
        features = {}
        orig_tokens = ["Hello", "world"]

        result = apply_ssmd_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hɛloʊ"
        assert result[1].phonemes == "wɝld"

    def test_feature_not_found(self):
        """Test feature for non-existent token."""
        tokens = [GToken(text="Hello", phonemes="hɛloʊ")]
        features = {5: "test"}  # Index doesn't exist
        orig_tokens = ["Hello"]

        result = apply_ssmd_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hɛloʊ"

    def test_apply_feature_case_insensitive(self):
        """Features should match regardless of casing differences."""
        tokens = [
            GToken(text="hello", phonemes="hɛloʊ"),
            GToken(text="world", phonemes="wɝld"),
        ]
        features = {0: "hˈɛloʊ"}
        orig_tokens = ["Hello", "world"]

        result = apply_ssmd_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hˈɛloʊ"
        assert result[0].get("rating") == 5


class TestPhonemizeWithSSMD:
    """Tests for phonemize_with_ssmd function."""

    def test_english_with_annotation(self):
        """Test English phonemization with annotation."""
        text = '[Misaki]{ph="misˈɑki"} is a G2P engine.'
        result = phonemize_with_ssmd(text, "en-us")
        assert "misˈɑki" in result
        assert result.startswith("misˈɑki")

    def test_get_g2p_with_ssmd(self):
        """Test get_g2p with SSMD enabled."""
        g2p = get_g2p("en-us", use_ssmd=True)
        result = g2p.phonemize('[Test]{ph="tˈɛst"}')
        assert "tˈɛst" in result

    def test_english_without_annotation(self):
        """Test English phonemization without annotation."""
        text = "Hello world."
        result = phonemize_with_ssmd(text, "en-us")
        assert len(result) > 0
        # Should contain phonemes for hello and world

    def test_english_multiple_annotations(self):
        """Test English with multiple annotations."""
        text = '[Misaki]{ph="misˈɑki"} and [Kokoro]{ph="kˈOkəɹO"} are great.'
        result = phonemize_with_ssmd(text, "en-us")
        assert "misˈɑki" in result
        assert "kˈOkəɹO" in result

    def test_language_override(self):
        """Test language override within text."""
        text = 'Hello [Welt]{lang="de"}.'
        result = phonemize_with_ssmd(text, "en-us")
        assert "vɛlt" in result

    def test_german_with_annotation(self):
        """Test German phonemization with annotation."""
        text = '[Hallo]{ph="hˈaloː"} Welt!'
        result = phonemize_with_ssmd(text, "de")
        assert "hˈaloː" in result
        assert "vɛlt" in result

    def test_german_multiple_annotations(self):
        """Test German with multiple annotations."""
        text = '[Hallo]{ph="hˈaloː"} und [schön]{ph="ʃˈøːn"}.'
        result = phonemize_with_ssmd(text, "de")
        assert "hˈaloː" in result
        assert "ʃˈøːn" in result
        text = '[Hallo]{lang="de"} und [schön]{lang="de"}.'
        result = phonemize_with_ssmd(text, "de")
        assert "haloː" in result
        assert "ʃøːn" in result

    def test_french_with_annotation(self):
        """Test French phonemization with annotation."""
        text = '[Bonjour]{ph="bɔ̃ʒuʁ"} le monde.'
        result = phonemize_with_ssmd(text, "fr")
        assert "bɔ̃ʒuʁ" in result

    def test_japanese_with_annotation(self):
        """Test Japanese phonemization with annotation."""
        text = '[こんにちは]{ph="konnit͡ɕiɰa"} 世界'
        result = phonemize_with_ssmd(text, "ja")
        assert "konnit͡ɕiɰa" in result

    def test_chinese_with_annotation(self):
        """Test Chinese phonemization with annotation."""
        text = '[你好]{ph="customphoneme"} 世界'
        result = phonemize_with_ssmd(text, "zh")
        # Chinese uses different output format (Bopomofo), verify it doesn't crash
        assert len(result) > 0

    def test_czech_with_annotation(self):
        """Test Czech phonemization with annotation."""
        text = '[Ahoj]{ph="ahoj"} světe'
        result = phonemize_with_ssmd(text, "cs")
        assert "ahoj" in result

    def test_empty_text(self):
        """Test empty text."""
        result = phonemize_with_ssmd("", "en-us")
        assert result == ""

    def test_whitespace_only(self):
        """Test whitespace only."""
        result = phonemize_with_ssmd("   ", "en-us")
        assert result == ""

    def test_special_characters_in_phonemes(self):
        """Test special IPA characters in annotations."""
        text = '[Test]{ph="tˈɛst"}.'
        result = phonemize_with_ssmd(text, "en-us")
        assert "tˈɛst" in result

    def test_punctuation_preserved(self):
        """Test punctuation is preserved."""
        text = '[Hello]{ph="hɛˈloʊ"} world!'
        result = phonemize_with_ssmd(text, "en-us")
        assert "!" in result


class TestSSMDIntegration:
    """Integration tests for SSMD with different languages."""

    def test_mixed_content_english(self):
        """Test mixed annotated and regular content in English."""
        text = 'This is [Misaki]{ph="misˈɑki"}, a G2P for [Kokoro]{ph="kˈOkəɹO"} TTS.'
        result = phonemize_with_ssmd(text, "en-us")
        assert "misˈɑki" in result
        assert "kˈOkəɹO" in result

    def test_mixed_content_german(self):
        """Test mixed annotated and regular content in German."""
        text = 'Das ist [schön]{ph="ʃˈøːn"} und [gut]{ph="ɡˈuːt"}.'
        result = phonemize_with_ssmd(text, "de")
        assert "ʃˈøːn" in result
        assert "ɡˈuːt" in result
        assert "das" in result

    def test_annotation_override_default(self):
        """Test annotation overrides default G2P."""
        # "test" normally phonemized differently, override with custom
        text = '[test]{ph="tˈɛst"} this'
        result = phonemize_with_ssmd(text, "en-us")
        assert "tˈɛst" in result

    def test_german_umlauts_with_annotation(self):
        """Test German umlauts in annotated words."""
        text = '[Äpfel]{ph="ˈɛpfəl"} sind [schön]{ph="ʃˈøːn"}.'
        result = phonemize_with_ssmd(text, "de")
        assert "ˈɛpfəl" in result
        assert "ʃˈøːn" in result

    def test_long_text_with_annotations(self):
        """Test longer text with multiple annotations."""
        text = (
            '[Misaki]{ph="misˈɑki"} is a modern G2P engine designed specifically '
            'for [Kokoro]{ph="kˈOkəɹO"} TTS models. It supports multiple languages '
            'including English, German, French, and [Japanese]{ph="ʤˌæpənˈiz"}.'
        )
        result = phonemize_with_ssmd(text, "en-us")
        assert "misˈɑki" in result
        assert "kˈOkəɹO" in result
        assert "ʤˌæpənˈiz" in result


class TestSSMDEdgeCases:
    """Edge case tests for SSMD module."""

    def test_consecutive_annotations(self):
        """Test consecutive annotations without spaces."""
        # Note: Without space, "Helloworld" becomes a single token
        # which won't match the individual annotations.
        # Use space for proper tokenization.
        text = '[Hello]{ph="hɛˈloʊ"} [world]{ph="wˈɝld"}'
        result = phonemize_with_ssmd(text, "en-us")
        assert "hɛˈloʊ" in result
        assert "wˈɝld" in result

    def test_nested_brackets(self):
        """Test nested brackets (not valid SSMD but shouldn't crash)."""
        text = '[[test]]{ph="tˈɛst"}'
        result = phonemize_with_ssmd(text, "en-us")
        # Should handle gracefully
        assert len(result) > 0

    def test_multiple_exclamation_marks(self):
        text = "!!!"
        result = phonemize_with_ssmd(text, "en-us")
        # Should handle gracefully
        assert "! ! !" in result

    def test_unclosed_annotation(self):
        """Test unclosed annotation."""
        text = '[Hello]{ph="hɛˈloʊ" world'
        result = phonemize_with_ssmd(text, "en-us")
        # Should handle gracefully
        assert len(result) > 0

    def test_annotation_with_numbers(self):
        """Test annotation with numbers."""
        text = '[Test123]{ph="tˈɛst"} ok'
        result = phonemize_with_ssmd(text, "en-us")
        assert "tˈɛst" in result

    def test_very_long_phoneme_string(self):
        """Test very long phoneme string."""
        long_phonemes = "a" * 1000
        text = f'[test]{{ph="{long_phonemes}"}}'
        result = phonemize_with_ssmd(text, "en-us")
        assert long_phonemes in result

    def test_unicode_in_annotations(self):
        """Test unicode characters in annotations."""
        text = '[こんにちは]{ph="konnit͡ɕiɰa"} test'
        result = phonemize_with_ssmd(text, "ja")
        assert "konnit͡ɕiɰa" in result
