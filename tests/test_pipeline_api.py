"""Tests for pipeline-friendly phonemization API."""

from kokorog2p import phonemize_to_result
from kokorog2p.types import OverrideSpan


class TestPhonemizeToResult:
    """Tests for phonemize_to_result function."""

    def test_simple_phonemization(self):
        """Test simple phonemization without overrides."""
        result = phonemize_to_result("Hello world!")

        assert result.clean_text == "Hello world!"
        assert len(result.tokens) > 0
        assert result.phonemes is not None
        assert len(result.phonemes) > 0
        assert result.token_ids is not None
        assert len(result.token_ids) > 0
        assert len(result.warnings) == 0

    def test_with_phoneme_override(self):
        """Test phonemization with phoneme override."""
        overrides = [OverrideSpan(0, 5, {"ph": "hɛˈloʊ"})]
        result = phonemize_to_result("Hello world!", overrides=overrides)

        assert "hɛˈloʊ" in result.phonemes
        assert len(result.warnings) == 0

    def test_with_language_override(self):
        """Test phonemization with language override."""
        overrides = [OverrideSpan(6, 10, {"lang": "de"})]
        result = phonemize_to_result("Hello Welt!", overrides=overrides, lang="en-us")

        # "Welt" should be phonemized as German
        assert result.tokens[1].lang == "de"
        assert len(result.phonemes) > 0

    def test_duplicate_words_with_different_overrides(self):
        """Test that duplicate words can have different phoneme overrides."""
        # "the" appears twice with different pronunciations
        overrides = [
            OverrideSpan(0, 3, {"ph": "ðə"}),  # First "the"
            OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the"
        ]
        result = phonemize_to_result("the cat the dog", overrides=overrides)

        # Both overrides should be applied
        assert "ðə" in result.phonemes
        assert "ði" in result.phonemes
        assert len(result.warnings) == 0

    def test_punctuation_handling(self):
        """Test that punctuation is handled correctly."""
        result = phonemize_to_result("Hello, world!")

        assert "," in result.phonemes or "!" in result.phonemes
        # Punctuation shouldn't cause warnings
        assert all("punctuation" not in w.lower() for w in result.warnings)

    def test_return_only_phonemes(self):
        """Test requesting only phonemes, not IDs."""
        result = phonemize_to_result("Hello!", return_ids=False, return_phonemes=True)

        assert result.phonemes is not None
        assert result.token_ids is None

    def test_return_only_ids(self):
        """Test requesting only IDs, not phonemes."""
        result = phonemize_to_result("Hello!", return_ids=True, return_phonemes=False)

        assert result.phonemes is None
        assert result.token_ids is not None
        assert len(result.token_ids) > 0
        assert all(isinstance(tid, int) for tid in result.token_ids)

    def test_return_ids_only_for_hello_world(self):
        """Test requesting only IDs, not phonemes, for 'Hello, world!'."""
        result = phonemize_to_result(
            "Hello, world!", return_ids=True, return_phonemes=False
        )

        assert result.token_ids is not None
        assert len(result.token_ids) > 0
        assert all(isinstance(tid, int) for tid in result.token_ids)
        assert result.phonemes is None
        assert not any("failed to convert" in w.lower() for w in result.warnings)

    def test_return_both(self):
        """Test requesting both phonemes and IDs."""
        result = phonemize_to_result("Hello!", return_ids=True, return_phonemes=True)

        assert result.phonemes is not None
        assert result.token_ids is not None

    def test_empty_text(self):
        """Test with empty text."""
        result = phonemize_to_result("")

        assert result.clean_text == ""
        assert len(result.tokens) == 0
        assert result.phonemes == ""

    def test_whitespace_only(self):
        """Test with whitespace-only text."""
        result = phonemize_to_result("   ")

        assert len(result.tokens) == 0
        assert result.phonemes == ""

    def test_legacy_alignment(self):
        """Test legacy word-based alignment."""
        overrides = [OverrideSpan(0, 5, {"ph": "hɛˈloʊ"})]
        result = phonemize_to_result(
            "Hello world!", overrides=overrides, alignment="legacy"
        )

        # Should still apply override
        assert "hɛˈloʊ" in result.phonemes

    def test_span_alignment_with_duplicates(self):
        """Test span alignment handles duplicates correctly."""
        # Both "the" instances should get separate overrides
        overrides = [
            OverrideSpan(0, 3, {"ph": "ðə"}),
            OverrideSpan(8, 11, {"ph": "ði"}),
        ]
        result = phonemize_to_result(
            "the cat the dog", overrides=overrides, alignment="span"
        )

        # Should have no warnings about duplicate alignment
        assert len(result.warnings) == 0

    def test_partial_overlap_warning(self):
        """Test that partial overlap generates warning."""
        # Override that partially overlaps token boundary
        overrides = [OverrideSpan(2, 8, {"ph": "test"})]
        result = phonemize_to_result("Hello world!", overrides=overrides)

        # Should have warning about snapping
        assert any(
            "snapping" in w.lower() or "overlap" in w.lower() for w in result.warnings
        )

    def test_no_overlap_warning(self):
        """Test that non-overlapping override generates warning."""
        # Override outside text range
        overrides = [OverrideSpan(100, 105, {"ph": "test"})]
        result = phonemize_to_result("Hello!", overrides=overrides)

        # Should warn about no overlap
        assert any("overlap" in w.lower() for w in result.warnings)

    def test_german_phonemization(self):
        """Test phonemization in German."""
        result = phonemize_to_result("Hallo Welt!", lang="de")

        assert result.phonemes is not None
        assert len(result.phonemes) > 0
        # German should phonemize "Hallo"
        assert len(result.warnings) == 0

    def test_multiple_language_switches(self):
        """Test multiple language switches in same text."""
        overrides = [
            OverrideSpan(6, 13, {"lang": "fr"}),  # "Bonjour"
            OverrideSpan(18, 22, {"lang": "de"}),  # "Welt"
        ]
        result = phonemize_to_result(
            "Hello Bonjour and Welt!", lang="en-us", overrides=overrides
        )

        # Should phonemize successfully with different languages
        assert result.phonemes is not None
        assert len(result.phonemes) > 0

    def test_custom_attributes_preserved(self):
        """Test that custom attributes are preserved in tokens."""
        overrides = [OverrideSpan(0, 5, {"rate": "fast", "volume": "loud"})]
        result = phonemize_to_result("Hello world!", overrides=overrides)

        # Custom attributes should be in token meta
        assert result.tokens[0].meta.get("rate") == "fast"
        assert result.tokens[0].meta.get("volume") == "loud"

    def test_phoneme_override_with_language(self):
        """Test phoneme override combined with language override."""
        overrides = [OverrideSpan(0, 7, {"ph": "bɔ̃ʒuʁ", "lang": "fr"})]
        result = phonemize_to_result(
            "Bonjour monde!", lang="en-us", overrides=overrides
        )

        # Phoneme override should be used (not language phonemization)
        assert "bɔ̃ʒuʁ" in result.phonemes
        assert result.tokens[0].lang == "fr"

    def test_reuse_g2p_instance(self):
        """Test reusing G2P instance for performance."""
        from kokorog2p import get_g2p

        g2p = get_g2p("en-us")
        result1 = phonemize_to_result("Hello!", g2p=g2p)
        result2 = phonemize_to_result("World!", g2p=g2p)

        assert result1.phonemes is not None
        assert result2.phonemes is not None

    def test_long_text_with_multiple_overrides(self):
        """Test longer text with multiple overrides."""
        text = "The quick brown fox jumps over the lazy dog."
        # "The" is at 0-3, "the" is at 31-34
        overrides = [
            OverrideSpan(0, 3, {"ph": "ði"}),  # "The"
            OverrideSpan(31, 34, {"ph": "ðə"}),  # "the" (second occurrence)
        ]
        result = phonemize_to_result(text, overrides=overrides)

        assert "ði" in result.phonemes
        assert "ðə" in result.phonemes
        assert len(result.warnings) == 0

    def test_contraction_apostrophe_s_preserved(self):
        """Test that contractions with 's preserve the apostrophe-s in phonemes.

        Bug: phonemize_to_result was dropping the 's in "What's", producing
        only 'wˌʌt' instead of something like 'wˌʌts' or 'wˌʌt s'.
        """
        result = phonemize_to_result("What's your problem?")

        # The input text should be preserved
        assert result.clean_text == "What's your problem?"

        # Check that "What's" is tokenized as a single token
        whats_token = None
        for token in result.tokens:
            if token.text == "What's":
                whats_token = token
                break

        assert whats_token is not None, "What's should be a single token"

        # The phonemes for "What's" should include both "what" and "'s" sounds
        # The 's in contractions is typically pronounced as /z/ or /s/
        whats_phonemes = whats_token.meta.get("phonemes", "")

        # Check that we have phonemes for "What's"
        assert whats_phonemes, "What's should have phonemes"

        # The phonemes should include some representation of the 's sound
        # Common phoneme representations: 's', 'z', 'ʃ' (depending on backend)
        # At minimum, the phonemes should be longer than just "what" alone
        # "what" alone is typically 3-4 phonemes (w-ʌ-t or similar)
        # "what's" should be 4-5+ phonemes
        assert len(whats_phonemes) > 4, (
            f"What's phonemes '{whats_phonemes}' seem incomplete. "
            f"Expected phonemes for both 'what' and 's', but got "
            f"only {len(whats_phonemes)} chars"
        )

        # Also verify the full phoneme string includes representation of both words
        assert result.phonemes is not None
        assert len(result.phonemes) > 0

    def test_matches_g2p_without_overrides(self):
        """Test that phonemize_to_result matches g2p output without overrides."""
        from kokorog2p import get_g2p

        text = "What's your problem?"
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        expected = g2p.phonemize(text)

        result = phonemize_to_result(text, g2p=g2p)

        assert result.phonemes == expected

    def test_various_contractions_preserved(self):
        """Test that various types of contractions preserve all phonemes."""
        test_cases = [
            ("It's raining", "It's"),
            ("I don't know", "don't"),
            ("We're ready", "We're"),
            ("They've gone", "They've"),
            ("She'll come", "She'll"),
        ]

        for text, contraction in test_cases:
            result = phonemize_to_result(text)

            # Find the contraction token
            contraction_token = None
            for token in result.tokens:
                if token.text == contraction:
                    contraction_token = token
                    break

            assert (
                contraction_token is not None
            ), f"{contraction} should be a token in '{text}'"

            # Check that it has phonemes
            phonemes = contraction_token.meta.get("phonemes", "")
            assert phonemes, f"{contraction} should have phonemes"

            # The phoneme string should not be empty for the full result
            assert result.phonemes is not None
            assert len(result.phonemes) > 0

    def test_hyphenated_words_preserved(self):
        """Test that hyphenated words like 'good-looking' are treated as single tokens.

        Hyphenated words should be tokenized as a single unit and all parts should
        be phonemized together.
        """
        result = phonemize_to_result("good-looking")

        # The input text should be preserved
        assert result.clean_text == "good-looking"

        # "good-looking" should be a single token
        assert len(result.tokens) == 1, (
            f"Expected 1 token for 'good-looking', got {len(result.tokens)}: "
            f"{[t.text for t in result.tokens]}"
        )

        token = result.tokens[0]
        assert token.text == "good-looking"

        # The phonemes should include both parts
        phonemes = token.meta.get("phonemes", "")
        assert phonemes, "good-looking should have phonemes"

        # Should have phonemes for both "good" and "looking"
        # At minimum, should be longer than just one word
        assert len(phonemes) > 5, (
            f"good-looking phonemes '{phonemes}' seem incomplete. "
            f"Expected phonemes for both 'good' and 'looking'"
        )

        # The full result should also be correct
        assert result.phonemes is not None
        assert len(result.phonemes) > 0

    def test_multiple_hyphenated_words(self):
        """Test sentences with multiple hyphenated words."""
        test_cases = [
            ("good-looking", 1),
            ("state-of-the-art technology", 2),  # "state-of-the-art" and "technology"
            ("A well-known actor", 3),  # "A", "well-known", "actor"
        ]

        for text, expected_tokens in test_cases:
            result = phonemize_to_result(text)

            # Check tokenization
            actual_tokens = len(result.tokens)
            assert actual_tokens == expected_tokens, (
                f"Expected {expected_tokens} tokens for '{text}', got {actual_tokens}: "
                f"{[t.text for t in result.tokens]}"
            )

            # Check that all tokens have phonemes
            for token in result.tokens:
                phonemes = token.meta.get("phonemes", "")
                assert phonemes, f"Token '{token.text}' should have phonemes"
