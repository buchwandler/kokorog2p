"""Tests for pipeline-friendly phonemization API."""

import pytest

from kokorog2p import phonemize
from kokorog2p.pipeline_api import phonemize_to_result
from kokorog2p.types import OverrideSpan


class TestPhonemizeToResult:
    """Tests for phonemize function."""

    def test_simple_phonemization(self):
        """Test simple phonemization without overrides."""
        result = phonemize("Hello world!")

        assert result.clean_text == "Hello world!"
        assert len(result.tokens) > 0
        assert result.phonemes is not None
        assert len(result.phonemes) > 0
        assert result.token_ids is not None
        assert len(result.token_ids) > 0
        assert len(result.warnings) == 0

        text = "'I can't... or shouldn't,' I replied."
        result = phonemize(text)
        assert result.phonemes == "“ˈI kˈænt…ɔɹ ʃˈʊdᵊnt,” ˈI ɹᵻplˈId."

        text = "But I'd've listened if you'd've given me a chance..."
        result = phonemize(text)
        assert result.phonemes == "bˌʌt ˈIdəv lˈɪsᵊnd ɪf jˈudəv ɡˈɪvən mˌi ɐ ʧˈæns…"

    @pytest.mark.espeak
    def test_span_alignment_espeak_spaced_ellipsis(self):
        """Ensure espeak span alignment doesn't duplicate words on ellipsis."""
        pytest.importorskip("espeakng_loader")

        text = "Hello . . . world!"
        result = phonemize(text, alignment="span", language="en-us", backend="espeak")

        assert result.clean_text == "Hello…world!"
        assert result.phonemes is not None
        assert result.phonemes.count("wˈɜɹld") == 1
        assert "…" in result.phonemes

        ellipsis_tokens = [t for t in result.tokens if t.text == "…"]
        assert len(ellipsis_tokens) == 1
        assert not ellipsis_tokens[0].meta.get("_drop")

    def test_with_phoneme_override(self):
        """Test phonemization with phoneme override."""
        overrides = [OverrideSpan(0, 5, {"ph": "hɛˈloʊ"})]
        result = phonemize("Hello world!", overrides=overrides)

        assert result.phonemes is not None
        assert "hɛˈloʊ" in result.phonemes
        assert len(result.warnings) == 0

    def test_phrase_ph_override_new_york_is_applied_once(self):
        """
        If an override span with 'ph' covers multiple tokens ("New" + "York"),
        the phonemes should appear ONCE in the output (not once per token).
        """
        text = "New York"
        # "New York" spans chars [0..8) in ASCII: New(0-3) space(3) York(4-8)
        overrides = [OverrideSpan(0, 8, {"ph": "nuː jɔːk"})]

        result = phonemize(text, overrides=overrides, language="en-us")

        assert result.phonemes is not None
        assert result.phonemes.count("nuː jɔːk") == 1, result.phonemes
        assert len(result.warnings) == 0

        # Optional: ensure it became a single token (only true if you implement merging)
        merged = [t for t in result.tokens if t.text == "New York"]
        assert len(merged) == 1
        assert merged[0].meta.get("ph") == "nuː jɔːk"
        assert merged[0].meta.get("phonemes") == "nuː jɔːk"

    def test_phrase_ph_override_new_york_twice_two_spans(self):
        """
        Spans are positional, so if the phrase appears twice,
        you need two OverrideSpans.
        This test ensures each occurrence is overridden (and each appears once).
        """
        text = "New York New York"
        # indices: first "New York" = 0..8, second "New York" = 9..17
        overrides = [
            OverrideSpan(0, 8, {"ph": "nuː jɔːk"}),
            OverrideSpan(9, 17, {"ph": "nuː jɔːk"}),
        ]

        result = phonemize(text, overrides=overrides, language="en-us")

        assert result.phonemes is not None
        assert result.phonemes.count("nuː jɔːk") == 2, result.phonemes
        assert len(result.warnings) == 0

    def test_with_multiple_phoneme_override(self):
        """Test phonemization with phoneme override."""
        overrides = [OverrideSpan(6, 14, {"ph": "nuː jɔːk"})]
        result = phonemize("Hello New York!", overrides=overrides)

        assert result.phonemes is not None
        assert "nuː jɔːk" in result.phonemes
        assert len(result.warnings) == 0

    def test_phrase_language_override_new_york_is_phonemized_in_english(self):
        """
        Override a multi-token phrase ("New York") with a language switch.
        This should force those tokens to be re-phonemized using the English G2P.
        """
        text = "Ich liebe New York."
        # Indices:
        # "Ich"(0-3) " "(3) "liebe"(4-9) " "(9) "New"(10-13) "
        # "(13) "York"(14-18) "."(18-19)
        overrides = [OverrideSpan(10, 18, {"lang": "en-us"})]

        result = phonemize(text, language="de", overrides=overrides)

        assert result.phonemes is not None and len(result.phonemes) > 0

        # Find the specific tokens
        new = next(t for t in result.tokens if t.text == "New")
        york = next(t for t in result.tokens if t.text == "York")
        ich = next(t for t in result.tokens if t.text == "Ich")

        # Language was applied to BOTH tokens in the phrase
        assert new.lang == "en-us"
        assert york.lang == "en-us"

        # They should have produced phonemes (i.e., they didn't disappear)
        assert new.meta.get("phonemes"), new.meta
        assert york.meta.get("phonemes"), york.meta

        # Surrounding tokens should NOT be marked as English
        assert ich.lang != "en-us"

        # Optional: keep this weaker if you sometimes get non-critical warnings
        assert not any(
            "failed to load" in w.lower() for w in result.warnings
        ), result.warnings

    def test_with_language_override(self):
        """Test phonemization with language override."""
        overrides = [OverrideSpan(6, 10, {"lang": "de"})]
        result = phonemize("Hello Welt!", overrides=overrides, language="en-us")

        # "Welt" should be phonemized as German
        assert result.tokens[1].lang == "de"
        assert result.phonemes is not None
        assert len(result.phonemes) > 0

    def test_duplicate_words_with_different_overrides(self):
        """Test that duplicate words can have different phoneme overrides."""
        # "the" appears twice with different pronunciations
        overrides = [
            OverrideSpan(0, 3, {"ph": "ðə"}),  # First "the"
            OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the"
        ]
        result = phonemize("the cat the dog", overrides=overrides)

        # Both overrides should be applied
        assert result.phonemes is not None
        assert "ðə" in result.phonemes
        assert "ði" in result.phonemes
        assert len(result.warnings) == 0

    def test_punctuation_handling(self):
        """Test that punctuation is handled correctly."""
        result = phonemize("Hello, world!")

        assert result.phonemes is not None
        assert "," in result.phonemes or "!" in result.phonemes
        # Punctuation shouldn't cause warnings
        assert all("punctuation" not in w.lower() for w in result.warnings)

    def test_punctuation_normalization_dash_ellipsis(self):
        """Ensure dash and ellipsis normalize to Kokoro punctuation."""
        from kokorog2p.vocab import validate_for_kokoro

        result = phonemize("Wait - now", language="en-us")
        assert result.phonemes is not None
        assert "—" in result.phonemes
        assert "-" not in result.phonemes
        assert validate_for_kokoro(result.phonemes)[0]

        result = phonemize("Bonjour — monde!", language="fr")
        assert result.phonemes is not None
        assert "—" in result.phonemes

        result = phonemize("Wait...what?!", language="en-us")
        assert result.phonemes is not None
        assert "…" in result.phonemes
        assert "..." not in result.phonemes

    def test_model_version_ids_v11(self):
        """Ensure IDs are encoded using the 1.1 vocab when required."""
        from kokorog2p.base import G2PBase
        from kokorog2p.token import GToken
        from kokorog2p.vocab import ids_to_phonemes, validate_for_kokoro

        class DummyZhG2P(G2PBase):
            def __init__(self):
                super().__init__(language="zh")

            def __call__(self, text: str) -> list[GToken]:
                return [
                    GToken(
                        text=text,
                        tag="X",
                        whitespace="",
                        phonemes="ㄋㄧ2ㄏㄠ3",
                    )
                ]

            def lookup(self, word: str, tag: str | None = None) -> str | None:
                return None

            def get_target_model(self) -> str:
                return "1.1"

        g2p = DummyZhG2P()
        result = phonemize_to_result(
            "nihao",
            lang="zh",
            g2p=g2p,
            return_ids=True,
            return_phonemes=True,
        )

        assert result.phonemes is not None
        assert result.token_ids is not None
        assert validate_for_kokoro(result.phonemes, model="1.1")[0]
        decoded = ids_to_phonemes(result.token_ids, model="1.1")
        assert decoded == result.phonemes

    def test_alignment_repeated_substrings(self):
        """Ensure repeated substrings keep deterministic overrides."""
        text = "the the the"
        overrides = [
            OverrideSpan(0, 3, {"ph": "ðə"}),
            OverrideSpan(4, 7, {"ph": "ði"}),
            OverrideSpan(8, 11, {"ph": "ðə"}),
        ]
        result = phonemize(text, overrides=overrides, alignment="span")

        assert result.phonemes is not None
        assert result.phonemes.count("ðə") == 2
        assert result.phonemes.count("ði") == 1
        assert not any("[ALIGNMENT]" in w for w in result.warnings)

    def test_abbreviation_sentence_phonemes(self):
        """Test abbreviations don't lose phonemes in sentences."""
        text = "Meet Mr. Schmidt, Mrs. Johnson, Ms. Anderson, and Dr. Brown."
        result = phonemize(text, language="en-us")

        assert not any("no phonemes" in w.lower() for w in result.warnings)

        token_map = {token.text: token for token in result.tokens}
        for abbrev in ("Mr.", "Mrs.", "Ms.", "Dr."):
            phonemes = token_map[abbrev].meta.get("phonemes", "")
            assert phonemes
            assert not phonemes.startswith(",")

        and_token = next(token for token in result.tokens if token.text == "and")
        assert and_token.meta.get("phonemes")

    def test_number_expansion_extended_text(self):
        """Test digit tokens expand into extended_text."""
        try:
            import num2words  # noqa: F401
        except ImportError:
            pytest.skip("num2words not installed")

        result = phonemize("I have 1 cat.", language="en-us")

        number_token = next(token for token in result.tokens if token.text == "1")
        assert number_token.extended_text
        assert number_token.extended_text != "1"
        assert number_token.meta.get("phonemes")
        assert result.extended_text is not None
        assert "one" in result.extended_text

    def test_temperature_expansion_extended_text(self):
        """Test temperature tokens expand into extended_text."""
        result = phonemize("It's 30C.", language="en-us")

        temp_token = next(token for token in result.tokens if token.text == "30C")
        assert temp_token.extended_text == "thirty degrees Celsius"
        assert temp_token.meta.get("phonemes")
        assert result.extended_text is not None
        assert "thirty degrees Celsius" in result.extended_text

    def test_abbreviation_expansion_metadata(self):
        """Ensure abbreviation expansion retains offsets and meta flag."""
        result = phonemize("Dr. Smith", language="en-us")

        token = next(token for token in result.tokens if token.text == "Dr.")
        assert token.char_start == 0
        assert token.char_end == 3
        assert token.extended_text
        assert token.meta.get("_extended_text_changed") is True

    def test_abbreviation_token_span(self):
        """Test that abbreviations with periods stay in one token."""
        result = phonemize("Hello Mr. Smith", language="en-us")

        token_texts = [token.text for token in result.tokens]
        assert "Mr." in token_texts
        assert "." not in token_texts

        mr_token = next(token for token in result.tokens if token.text == "Mr.")
        assert mr_token.char_start == 6
        assert mr_token.char_end == 9

    def test_return_only_phonemes(self):
        """Test requesting only phonemes, not IDs."""
        result = phonemize("Hello!", return_ids=False, return_phonemes=True)

        assert result.phonemes is not None
        assert len(result.token_ids) == 0

    def test_return_only_ids(self):
        """Test requesting only IDs, not phonemes."""
        result = phonemize("Hello!", return_ids=True, return_phonemes=False)

        assert result.phonemes == ""
        assert result.token_ids is not None
        assert len(result.token_ids) > 0
        assert all(isinstance(tid, int) for tid in result.token_ids)

    def test_return_ids_only_for_hello_world(self):
        """Test requesting only IDs, not phonemes, for 'Hello, world!'."""
        result = phonemize("Hello, world!", return_ids=True, return_phonemes=False)

        assert result.token_ids is not None
        assert len(result.token_ids) > 0
        assert all(isinstance(tid, int) for tid in result.token_ids)
        assert result.phonemes == ""
        assert not any("failed to convert" in w.lower() for w in result.warnings)

    def test_return_both(self):
        """Test requesting both phonemes and IDs."""
        result = phonemize("Hello!", return_ids=True, return_phonemes=True)

        assert result.phonemes is not None
        assert result.token_ids is not None

    def test_empty_text(self):
        """Test with empty text."""
        result = phonemize("")

        assert result.clean_text == ""
        assert len(result.tokens) == 0
        assert result.phonemes == ""

    def test_whitespace_only(self):
        """Test with whitespace-only text."""
        result = phonemize("   ")

        assert len(result.tokens) == 0
        assert result.phonemes == ""

    def test_legacy_alignment(self):
        """Test legacy word-based alignment."""
        overrides = [OverrideSpan(0, 5, {"ph": "hɛˈloʊ"})]
        result = phonemize("Hello world!", overrides=overrides, alignment="legacy")

        # Should still apply override
        assert result.phonemes is not None
        assert "hɛˈloʊ" in result.phonemes

    def test_span_alignment_with_duplicates(self):
        """Test span alignment handles duplicates correctly."""
        # Both "the" instances should get separate overrides
        overrides = [
            OverrideSpan(0, 3, {"ph": "ðə"}),
            OverrideSpan(8, 11, {"ph": "ði"}),
        ]
        result = phonemize("the cat the dog", overrides=overrides, alignment="span")

        # Should have no warnings about duplicate alignment
        assert len(result.warnings) == 0

    def test_partial_overlap_warning(self):
        """Test that partial overlap generates warning."""
        # Override that partially overlaps token boundary
        overrides = [OverrideSpan(2, 8, {"ph": "test"})]
        result = phonemize("Hello world!", overrides=overrides)

        # Should have warning about snapping
        assert any(
            "snapping" in w.lower() or "overlap" in w.lower() for w in result.warnings
        )
        assert any("[2:8]" in w for w in result.warnings)

    def test_no_overlap_warning(self):
        """Test that non-overlapping override generates warning."""
        # Override outside text range
        overrides = [OverrideSpan(100, 105, {"ph": "test"})]
        result = phonemize("Hello!", overrides=overrides)

        # Should warn about no overlap
        assert any("overlap" in w.lower() for w in result.warnings)
        assert any("[100:105]" in w for w in result.warnings)

    def test_german_phonemization(self):
        """Test phonemization in German."""
        result = phonemize("Hallo Welt!", language="de")

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
        result = phonemize(
            "Hello Bonjour and Welt!", language="en-us", overrides=overrides
        )

        # Should phonemize successfully with different languages
        assert result.phonemes is not None
        assert len(result.phonemes) > 0

    def test_custom_attributes_preserved(self):
        """Test that custom attributes are preserved in tokens."""
        overrides = [OverrideSpan(0, 5, {"rate": "fast", "volume": "loud"})]
        result = phonemize("Hello world!", overrides=overrides)

        # Custom attributes should be in token meta
        assert result.tokens[0].meta.get("rate") == "fast"
        assert result.tokens[0].meta.get("volume") == "loud"

    def test_phoneme_override_with_language(self):
        """Test phoneme override combined with language override."""
        overrides = [OverrideSpan(0, 7, {"ph": "bɔ̃ʒuʁ", "lang": "fr"})]
        result = phonemize("Bonjour monde!", language="en-us", overrides=overrides)

        # Phoneme override should be used (not language phonemization)
        assert result.phonemes is not None
        assert "bɔ̃ʒuʁ" in result.phonemes
        assert result.tokens[0].lang == "fr"

    def test_reuse_g2p_instance(self):
        """Test reusing G2P instance for performance."""
        from kokorog2p import get_g2p

        g2p = get_g2p("en-us", use_spacy=False)
        result1 = phonemize_to_result("Hello!", g2p=g2p)
        result2 = phonemize_to_result("World!", g2p=g2p)

        assert result1.phonemes is not None
        assert result2.phonemes is not None

    def test_normalizer_state_restored(self):
        """Ensure normalizer abbreviation settings are restored after calls."""
        from kokorog2p import get_g2p

        g2p = get_g2p("en-us", use_spacy=False)
        normalizer = getattr(g2p, "_normalizer", None) or getattr(
            g2p, "normalizer", None
        )
        if normalizer is None or not hasattr(normalizer, "expand_abbreviations"):
            pytest.skip("G2P normalizer not available")

        original_expand = normalizer.expand_abbreviations
        phonemize_to_result("Dr. Smith", g2p=g2p)
        assert normalizer.expand_abbreviations == original_expand

    @pytest.mark.slow
    def test_normalizer_thread_safety(self):
        """Ensure concurrent calls do not corrupt normalizer state."""
        from concurrent.futures import ThreadPoolExecutor

        from kokorog2p import get_g2p

        g2p = get_g2p("en-us")
        normalizer = getattr(g2p, "_normalizer", None) or getattr(
            g2p, "normalizer", None
        )
        if normalizer is None or not hasattr(normalizer, "expand_abbreviations"):
            pytest.skip("G2P normalizer not available")

        text = "Dr. Smith arrived."

        original_expand = normalizer.expand_abbreviations

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(
                executor.map(
                    lambda _: phonemize_to_result(text, g2p=g2p).phonemes,
                    range(16),
                )
            )

        assert all(result == results[0] for result in results)
        assert normalizer.expand_abbreviations == original_expand

    def test_long_text_with_multiple_overrides(self):
        """Test longer text with multiple overrides."""
        text = "The quick brown fox jumps over the lazy dog."
        # "The" is at 0-3, "the" is at 31-34
        overrides = [
            OverrideSpan(0, 3, {"ph": "ði"}),  # "The"
            OverrideSpan(31, 34, {"ph": "ðə"}),  # "the" (second occurrence)
        ]
        result = phonemize(text, overrides=overrides)

        assert result.phonemes is not None
        assert "ði" in result.phonemes
        assert "ðə" in result.phonemes
        assert len(result.warnings) == 0

    def test_contraction_apostrophe_s_preserved(self):
        """Test that contractions with 's preserve the apostrophe-s in phonemes.

        Bug: phonemize was dropping the 's in "What's", producing
        only 'wˌʌt' instead of something like 'wˌʌts' or 'wˌʌt s'.
        """
        result = phonemize("What's your problem?")

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
        """Test that phonemize matches g2p output without overrides."""
        from kokorog2p import get_g2p

        text = "What's your problem?"
        g2p = get_g2p("en-us")
        expected = g2p.phonemize(text)

        result = phonemize(text)

        assert result.phonemes == expected

    def test_normalization_alignment_preserves_pronouns(self):
        """Ensure G2P normalization doesn't drop token phonemes."""
        from kokorog2p import get_g2p

        text = "'I can't... or shouldn't,' I replied."
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        expected = g2p.phonemize(text)
        assert result.phonemes == expected

        i_tokens = [token for token in result.tokens if token.text == "I"]
        assert len(i_tokens) == 2
        assert all(token.meta.get("phonemes") for token in i_tokens)

    def test_nested_contractions_with_quotes(self):
        """Ensure nested contractions survive spaCy punctuation tags."""
        from kokorog2p import get_g2p

        text = (
            "'I'd've liked to've met you sooner...' he said. "
            "\"Maybe things'd've been different...\""
        )
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

        token = next(token for token in result.tokens if token.text == "things'd've")
        assert token.meta.get("phonemes")

    def test_leading_quote_does_not_duplicate_pronoun(self):
        """Ensure quote+word spans don't double count phonemes."""
        from kokorog2p import get_g2p

        text = (
            "His words hung in the air like smoke... "
            "\"I can't... or shouldn't,\" I replied, confused by his hostility.'"
        )
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

        i_tokens = [token for token in result.tokens if token.text == "I"]
        assert len(i_tokens) == 2
        assert all(token.meta.get("phonemes") for token in i_tokens)

    def test_adjacent_quotes_without_space(self):
        """Ensure back-to-back quotes don't duplicate words."""
        from kokorog2p import get_g2p

        text = "He said, \"I\" 'I'."
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

        i_tokens = [token for token in result.tokens if token.text == "I"]
        assert len(i_tokens) == 2
        assert all(token.meta.get("phonemes") for token in i_tokens)

    def test_punctuation_inside_quotes(self):
        """Ensure quoted punctuation doesn't duplicate pronouns."""
        from kokorog2p import get_g2p

        text = '"I," he said. "I."'
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

        i_tokens = [token for token in result.tokens if token.text == "I"]
        assert len(i_tokens) == 2
        assert all(token.meta.get("phonemes") for token in i_tokens)

    def test_nested_quotes_with_contractions(self):
        """Ensure nested quotes keep contraction phonemes."""
        from kokorog2p import get_g2p

        text = "He said, \"She whispered, 'I'd've...'.\""
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

        token = next(token for token in result.tokens if token.text == "I'd've")
        assert token.meta.get("phonemes")

    def test_multiple_ellipsis_positions(self):
        """Ensure multiple ellipses normalize without drift."""
        from kokorog2p import get_g2p

        text = "Wait... now... later..."
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

    def test_contractions_with_trailing_punctuation(self):
        """Ensure contractions with punctuation keep phonemes."""
        from kokorog2p import get_g2p

        text = "\"I'd've,\" she paused. \"You'd've.\""
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

        contractions = {"I'd've", "You'd've"}
        for contraction in contractions:
            token = next(token for token in result.tokens if token.text == contraction)
            assert token.meta.get("phonemes")

    def test_abbreviation_inside_quotes_with_ellipsis(self):
        """Ensure abbreviations inside quotes keep phonemes."""
        from kokorog2p import get_g2p

        text = 'He said, "Dr. Smith..." and left.'
        g2p = get_g2p("en-us", markdown_syntax="disabled")
        result = phonemize(text)

        assert result.phonemes == g2p.phonemize(text)

        dr_token = next(token for token in result.tokens if token.text == "Dr.")
        assert dr_token.meta.get("phonemes")

    def test_language_override_inside_quotes(self):
        """Ensure language overrides survive quoted text."""
        text = 'She said, "Hallo Welt!"'
        start = text.index("Welt")
        overrides = [OverrideSpan(start, start + len("Welt"), {"lang": "de"})]

        result = phonemize(text, language="en-us", overrides=overrides)

        token = next(token for token in result.tokens if token.text == "Welt")
        assert token.lang == "de"
        assert token.meta.get("phonemes")

    def test_override_inside_quoted_word(self):
        """Ensure overrides apply when G2P merges quote+word spans."""
        text = 'He said, "I."'
        start = text.index("I")
        overrides = [OverrideSpan(start, start + 1, {"ph": "ˈaI"})]

        result = phonemize(text, overrides=overrides)

        token = next(token for token in result.tokens if token.text == "I")
        assert token.meta.get("phonemes") == "ˈaI"
        assert result.phonemes is not None
        assert result.phonemes.count("ˈaI") == 1

    def test_various_contractions_preserved(self):
        """Test that various types of contractions preserve all phonemes."""
        test_cases = [
            ("It's raining", "It's"),
            ("I don't know", "don't"),
            ("We're ready", "We're"),
            ("They've gone", "They've"),
            ("She'll come", "She'll"),
            ("I'd've listened", "I'd've"),
        ]

        for text, contraction in test_cases:
            result = phonemize(text)

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
        result = phonemize("good-looking")

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
            result = phonemize(text)

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
