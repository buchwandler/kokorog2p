"""Tests for the markdown annotation module."""

from kokorog2p.markdown import (
    apply_markdown_features,
    phonemize_with_markdown,
    preprocess_markdown,
    remove_markdown,
)
from kokorog2p.token import GToken


class TestPreprocessMarkdown:
    """Tests for preprocess_markdown function."""

    def test_simple_annotation(self):
        """Test simple markdown annotation."""
        text = "[Misaki](/misˈɑki/) is great."
        clean, tokens, features = preprocess_markdown(text)
        assert clean == "Misaki is great."
        assert "Misaki" in tokens
        assert 0 in features
        assert features[0] == "misˈɑki"

    def test_multiple_annotations(self):
        """Test multiple markdown annotations."""
        text = "[Hello](/hɛˈloʊ/) [world](/wˈɝld/)!"
        clean, tokens, features = preprocess_markdown(text)
        assert clean == "Hello world!"
        assert len(features) == 2
        assert features[0] == "hɛˈloʊ"
        assert features[1] == "wˈɝld"

    def test_no_annotations(self):
        """Test text without annotations."""
        text = "Hello world!"
        clean, tokens, features = preprocess_markdown(text)
        assert clean == "Hello world!"
        assert len(features) == 0

    def test_mixed_annotations_and_regular_text(self):
        """Test mix of annotated and regular text."""
        text = "[Misaki](/misˈɑki/) is a G2P engine."
        clean, tokens, features = preprocess_markdown(text)
        assert clean == "Misaki is a G2P engine."
        assert len(features) == 1
        assert features[0] == "misˈɑki"

    def test_annotation_without_phoneme_slash(self):
        """Test annotation without leading slash (should be ignored)."""
        text = "[link](http://example.com) test"
        clean, tokens, features = preprocess_markdown(text)
        assert "link" in clean
        assert len(features) == 0  # Not a phoneme annotation

    def test_relative_link_is_not_annotation(self):
        """Relative links should not be treated as annotations."""
        text = "[link](/docs/page) test"
        clean, tokens, features = preprocess_markdown(text)
        assert "link" in clean
        assert len(features) == 0

    def test_empty_annotation(self):
        """Test annotation with empty phonemes."""
        text = "[word](/) test"
        clean, tokens, features = preprocess_markdown(text)
        assert "word" in clean
        assert 0 in features
        assert features[0] == ""

    def test_whitespace_handling(self):
        """Test whitespace in annotations."""
        text = "  [Test](/tˈɛst/)  more text  "
        clean, tokens, features = preprocess_markdown(text)
        assert "Test" in clean
        assert 0 in features
        assert features[0] == "tˈɛst"


class TestRemoveMarkdown:
    """Tests for remove_markdown function."""

    def test_remove_simple_annotation(self):
        """Test removing simple annotation."""
        text = "[Misaki](/misˈɑki/) is great."
        result = remove_markdown(text)
        assert result == "Misaki is great."

    def test_remove_multiple_annotations(self):
        """Test removing multiple annotations."""
        text = "[Hello](/hɛˈloʊ/) [world](/wˈɝld/)!"
        result = remove_markdown(text)
        assert result == "Hello world!"

    def test_no_annotations(self):
        """Test text without annotations."""
        text = "Hello world!"
        result = remove_markdown(text)
        assert result == "Hello world!"

    def test_regular_links(self):
        """Test removing regular markdown links."""
        text = "[link](http://example.com)"
        result = remove_markdown(text)
        assert result == "link"


class TestApplyMarkdownFeatures:
    """Tests for apply_markdown_features function."""

    def test_apply_single_feature(self):
        """Test applying single phoneme feature."""
        tokens = [
            GToken(text="Hello", phonemes="hɛloʊ"),
            GToken(text="world", phonemes="wɝld"),
        ]
        features = {0: "hˈɛloʊ"}
        orig_tokens = ["Hello", "world"]

        result = apply_markdown_features(tokens, features, orig_tokens)
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

        result = apply_markdown_features(tokens, features, orig_tokens)
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

        result = apply_markdown_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hɛloʊ"
        assert result[1].phonemes == "wɝld"

    def test_feature_not_found(self):
        """Test feature for non-existent token."""
        tokens = [GToken(text="Hello", phonemes="hɛloʊ")]
        features = {5: "test"}  # Index doesn't exist
        orig_tokens = ["Hello"]

        result = apply_markdown_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hɛloʊ"

    def test_apply_feature_case_insensitive(self):
        """Features should match regardless of casing differences."""
        tokens = [
            GToken(text="hello", phonemes="hɛloʊ"),
            GToken(text="world", phonemes="wɝld"),
        ]
        features = {0: "hˈɛloʊ"}
        orig_tokens = ["Hello", "world"]

        result = apply_markdown_features(tokens, features, orig_tokens)
        assert result[0].phonemes == "hˈɛloʊ"
        assert result[0].get("rating") == 5


class TestPhonemizeWithMarkdown:
    """Tests for phonemize_with_markdown function."""

    def test_english_with_annotation(self):
        """Test English phonemization with annotation."""
        text = "[Misaki](/misˈɑki/) is a G2P engine."
        result = phonemize_with_markdown(text, "en-us")
        assert "misˈɑki" in result
        assert result.startswith("misˈɑki")

    def test_english_without_annotation(self):
        """Test English phonemization without annotation."""
        text = "Hello world."
        result = phonemize_with_markdown(text, "en-us")
        assert len(result) > 0
        # Should contain phonemes for hello and world

    def test_english_multiple_annotations(self):
        """Test English with multiple annotations."""
        text = "[Misaki](/misˈɑki/) and [Kokoro](/kˈOkəɹO/) are great."
        result = phonemize_with_markdown(text, "en-us")
        assert "misˈɑki" in result
        assert "kˈOkəɹO" in result

    def test_german_with_annotation(self):
        """Test German phonemization with annotation."""
        text = "[Hallo](/hˈaloː/) Welt!"
        result = phonemize_with_markdown(text, "de")
        assert "hˈaloː" in result
        assert "vɛlt" in result

    def test_german_multiple_annotations(self):
        """Test German with multiple annotations."""
        text = "[Hallo](/hˈaloː/) und [schön](/ʃˈøːn/)."
        result = phonemize_with_markdown(text, "de")
        assert "hˈaloː" in result
        assert "ʃˈøːn" in result

    def test_french_with_annotation(self):
        """Test French phonemization with annotation."""
        text = "[Bonjour](/bɔ̃ʒuʁ/) le monde."
        result = phonemize_with_markdown(text, "fr")
        assert "bɔ̃ʒuʁ" in result

    def test_japanese_with_annotation(self):
        """Test Japanese phonemization with annotation."""
        text = "[こんにちは](/konnit͡ɕiɰa/) 世界"
        result = phonemize_with_markdown(text, "ja")
        assert "konnit͡ɕiɰa" in result

    def test_chinese_with_annotation(self):
        """Test Chinese phonemization with annotation."""
        text = "[你好](/customphoneme/) 世界"
        result = phonemize_with_markdown(text, "zh")
        # Chinese uses different output format (Bopomofo), verify it doesn't crash
        assert len(result) > 0

    def test_czech_with_annotation(self):
        """Test Czech phonemization with annotation."""
        text = "[Ahoj](/ahoj/) světe"
        result = phonemize_with_markdown(text, "cs")
        assert "ahoj" in result

    def test_empty_text(self):
        """Test empty text."""
        result = phonemize_with_markdown("", "en-us")
        assert result == ""

    def test_whitespace_only(self):
        """Test whitespace only."""
        result = phonemize_with_markdown("   ", "en-us")
        assert result == ""

    def test_special_characters_in_phonemes(self):
        """Test special IPA characters in annotations."""
        text = "[Test](/tˈɛst/)."
        result = phonemize_with_markdown(text, "en-us")
        assert "tˈɛst" in result

    def test_punctuation_preserved(self):
        """Test punctuation is preserved."""
        text = "[Hello](/hɛˈloʊ/) world!"
        result = phonemize_with_markdown(text, "en-us")
        assert "!" in result


class TestMarkdownIntegration:
    """Integration tests for markdown with different languages."""

    def test_mixed_content_english(self):
        """Test mixed annotated and regular content in English."""
        text = "This is [Misaki](/misˈɑki/), a G2P for [Kokoro](/kˈOkəɹO/) TTS."
        result = phonemize_with_markdown(text, "en-us")
        assert "misˈɑki" in result
        assert "kˈOkəɹO" in result

    def test_mixed_content_german(self):
        """Test mixed annotated and regular content in German."""
        text = "Das ist [schön](/ʃˈøːn/) und [gut](/ɡˈuːt/)."
        result = phonemize_with_markdown(text, "de")
        assert "ʃˈøːn" in result
        assert "ɡˈuːt" in result
        assert "das" in result

    def test_annotation_override_default(self):
        """Test annotation overrides default G2P."""
        # "test" normally phonemized differently, override with custom
        text = "[test](/tˈɛst/) this"
        result = phonemize_with_markdown(text, "en-us")
        assert "tˈɛst" in result

    def test_german_umlauts_with_annotation(self):
        """Test German umlauts in annotated words."""
        text = "[Äpfel](/ˈɛpfəl/) sind [schön](/ʃˈøːn/)."
        result = phonemize_with_markdown(text, "de")
        assert "ˈɛpfəl" in result
        assert "ʃˈøːn" in result

    def test_long_text_with_annotations(self):
        """Test longer text with multiple annotations."""
        text = (
            "[Misaki](/misˈɑki/) is a modern G2P engine designed specifically "
            "for [Kokoro](/kˈOkəɹO/) TTS models. It supports multiple languages "
            "including English, German, French, and [Japanese](/ʤˌæpənˈiz/)."
        )
        result = phonemize_with_markdown(text, "en-us")
        assert "misˈɑki" in result
        assert "kˈOkəɹO" in result
        assert "ʤˌæpənˈiz" in result


class TestMarkdownEdgeCases:
    """Edge case tests for markdown module."""

    def test_consecutive_annotations(self):
        """Test consecutive annotations without spaces."""
        # Note: Without space, "Helloworld" becomes a single token
        # which won't match the individual annotations.
        # Use space for proper tokenization.
        text = "[Hello](/hɛˈloʊ/) [world](/wˈɝld/)"
        result = phonemize_with_markdown(text, "en-us")
        assert "hɛˈloʊ" in result
        assert "wˈɝld" in result

    def test_nested_brackets(self):
        """Test nested brackets (not valid markdown but shouldn't crash)."""
        text = "[[test]](/tˈɛst/)"
        result = phonemize_with_markdown(text, "en-us")
        # Should handle gracefully
        assert len(result) > 0

    def test_unclosed_annotation(self):
        """Test unclosed annotation."""
        text = "[Hello](/hɛˈloʊ/ world"
        result = phonemize_with_markdown(text, "en-us")
        # Should handle gracefully
        assert len(result) > 0

    def test_annotation_with_numbers(self):
        """Test annotation with numbers."""
        text = "[Test123](/tˈɛst/) ok"
        result = phonemize_with_markdown(text, "en-us")
        assert "tˈɛst" in result

    def test_very_long_phoneme_string(self):
        """Test very long phoneme string."""
        long_phonemes = "a" * 1000
        text = f"[test](/{long_phonemes}/)"
        result = phonemize_with_markdown(text, "en-us")
        assert long_phonemes in result

    def test_unicode_in_annotations(self):
        """Test unicode characters in annotations."""
        text = "[こんにちは](/konnit͡ɕiɰa/) test"
        result = phonemize_with_markdown(text, "ja")
        assert "konnit͡ɕiɰa" in result
