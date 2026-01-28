"""Tests for the English G2P module."""

from typing import Literal

import pytest

from kokorog2p import phonemize_to_result
from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.token import GToken


def phonemize_with_backend(
    backend: Literal["g2p", "pipeline"],
    g2p: EnglishG2P,
    text: str,
) -> str:
    if backend == "g2p":
        return g2p.phonemize(text)
    return phonemize_to_result(text, g2p=g2p).phonemes or ""


@pytest.fixture(params=["g2p", "pipeline"])
def phoneme_backend(request: pytest.FixtureRequest) -> Literal["g2p", "pipeline"]:
    return request.param


class TestEnglishG2PNoFallback:
    """Tests for EnglishG2P without espeak fallback."""

    def test_creation(self, english_g2p_no_espeak):
        """Test G2P creation."""
        assert english_g2p_no_espeak.language == "en-us"
        assert english_g2p_no_espeak.use_espeak_fallback is False
        assert english_g2p_no_espeak.use_spacy is False

    def test_is_british(self, english_g2p_no_espeak):
        """Test is_british property."""
        assert english_g2p_no_espeak.is_british is False

    def test_call_returns_tokens(self, english_g2p_no_espeak):
        """Test calling G2P returns list of tokens."""
        tokens = english_g2p_no_espeak("hello world")
        assert isinstance(tokens, list)
        assert all(isinstance(t, GToken) for t in tokens)

    def test_known_word_phonemization(self, english_g2p_no_espeak):
        """Test phonemizing known words."""
        tokens = english_g2p_no_espeak("hello")
        assert len(tokens) >= 1
        # "hello" should be in the dictionary
        assert tokens[0].phonemes is not None
        assert tokens[0].text == "hello"

    def test_unknown_word_without_fallback(self, english_g2p_no_espeak):
        """Test unknown word without fallback uses unk marker."""
        tokens = english_g2p_no_espeak("xyzqwerty")
        assert len(tokens) >= 1
        # Should get the unk marker
        assert tokens[0].phonemes == english_g2p_no_espeak.unk

    def test_empty_input(self, english_g2p_no_espeak):
        """Test empty input returns empty list."""
        tokens = english_g2p_no_espeak("")
        assert tokens == []

        tokens2 = english_g2p_no_espeak("   ")
        assert tokens2 == []

    def test_phonemize_method(self, english_g2p_no_espeak, phoneme_backend):
        """Test phonemize method returns string."""
        result = phonemize_with_backend(phoneme_backend, english_g2p_no_espeak, "hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_lookup_method(self, english_g2p_no_espeak):
        """Test lookup method."""
        ps = english_g2p_no_espeak.lookup("hello")
        assert ps is not None
        assert isinstance(ps, str)

        # Unknown word
        ps2 = english_g2p_no_espeak.lookup("xyzqwerty")
        assert ps2 is None

    def test_repr(self, english_g2p_no_espeak):
        """Test string representation."""
        result = repr(english_g2p_no_espeak)
        assert "EnglishG2P" in result
        assert "en-us" in result

    def test_multiple_exlamation_marks(self, english_g2p_no_espeak):
        """Test !!!."""
        tokens = english_g2p_no_espeak("!!!")
        assert len(tokens) == 3
        # All should have phonemes with fallback
        for token in tokens:
            assert token.phonemes == "!"


@pytest.mark.espeak
class TestEnglishG2PWithEspeak:
    """Tests for EnglishG2P with espeak fallback."""

    def test_unknown_word_with_fallback(self, english_g2p_with_espeak):
        """Test unknown word uses espeak fallback."""
        tokens = english_g2p_with_espeak("xyzqwerty")
        assert len(tokens) >= 1
        # With fallback, should get actual phonemes (not unk marker)
        # Unless espeak also fails
        phonemes = tokens[0].phonemes
        assert phonemes is not None

    def test_mixed_known_unknown(self, english_g2p_with_espeak):
        """Test mixing known and unknown words."""
        tokens = english_g2p_with_espeak("hello xyzqwerty world")
        assert len(tokens) >= 3
        # All should have phonemes with fallback
        for token in tokens:
            if token.is_word:
                assert token.phonemes is not None

    def test_multiple_exlamation_marks(self, english_g2p_with_espeak):
        """Test !!!."""
        tokens = english_g2p_with_espeak("!!!")
        assert len(tokens) == 3
        # All should have phonemes with fallback
        for token in tokens:
            assert token.phonemes == "!"


@pytest.mark.spacy
class TestEnglishG2PWithSpacy:
    """Tests for EnglishG2P with spaCy."""

    def test_creation_with_spacy(self, english_g2p_with_spacy):
        """Test G2P creation with spaCy."""
        assert english_g2p_with_spacy.use_spacy is True

    def test_pos_tagging(self, english_g2p_with_spacy):
        """Test that POS tags are assigned."""
        tokens = english_g2p_with_spacy("The cat sat on the mat.")
        # With spaCy, tokens should have POS tags
        word_tokens = [t for t in tokens if t.is_word]
        assert any(t.tag != "" for t in word_tokens)

    def test_punctuation_handling(self, english_g2p_with_spacy):
        """Test punctuation is handled correctly."""
        tokens = english_g2p_with_spacy("Hello, world!")
        # Should have punctuation tokens
        assert any(t.text == "," for t in tokens)
        assert any(t.text == "!" for t in tokens)

    def test_multiple_exlamation_marks(self, english_g2p_with_spacy):
        """Test !!!."""
        tokens = english_g2p_with_spacy("!!!")
        assert len(tokens) == 3
        # All should have phonemes with fallback
        for token in tokens:
            assert token.phonemes == "!"

    def test_punctuation_with_quotes(self, english_g2p_with_spacy, phoneme_backend):
        """Test that punctuation followed by quotes is preserved as punctuation.

        This is a regression test for the issue where !' and !" were being looked up
        in the lexicon and matching 'exclamation' instead of being treated
        as punctuation.
        """
        # Test case 1: Single quotes with punctuation
        tokens = english_g2p_with_spacy("'Master Maker!'")
        phonemes = phonemize_with_backend(
            phoneme_backend, english_g2p_with_spacy, "'Master Maker!'"
        )

        # The ! should remain as punctuation, not be converted to "exclamation"
        assert (
            "ˈɛkskləmˌAʃən" not in phonemes
        ), f"! should not be converted to 'exclamation'. Got: {phonemes!r}"
        assert "!" in phonemes, f"! should be preserved. Got: {phonemes!r}"

        # Check tokens
        punct_tokens = [t for t in tokens if "!" in t.text]
        if punct_tokens:
            for t in punct_tokens:
                # Punctuation should not have word phonemes
                assert "ɛkskləm" not in str(t.phonemes), (
                    f"Token {t.text!r} should be punctuation, not word. "
                    f"Phonemes: {t.phonemes!r}"
                )

        # Test case 2: Double quotes with punctuation
        phonemes2 = phonemize_with_backend(
            phoneme_backend, english_g2p_with_spacy, '"Hello!"'
        )

        assert (
            "ˈɛkskləmˌAʃən" not in phonemes2
        ), f"! should not be converted to 'exclamation'. Got: {phonemes2!r}"
        assert "!" in phonemes2, f"! should be preserved. Got: {phonemes2!r}"

        # Test case 3: Various punctuation+quote combinations
        test_cases = [
            ("Hello?'", "?"),
            ("Wait!'", "!"),
            ("Really.'", "."),
            ("'Hello!'", "!"),
            ('"Hello!"', "!"),
            ('"Stop?"', "?"),
            ('"Wait…"', "…"),  # Use actual ellipsis character
            ("'Amazing!'", "!"),
        ]

        for text, expected_punct in test_cases:
            result = phonemize_with_backend(
                phoneme_backend, english_g2p_with_spacy, text
            )
            # Check punctuation is preserved
            assert (
                expected_punct in result
            ), f"For '{text}', expected '{expected_punct}' in result. Got: {result!r}"
            # Check NOT converted to word
            assert "ɛkskləm" not in result, (
                f"For '{text}', punctuation should not be converted to word. "
                f"Got: {result!r}"
            )

    def test_contraction_phonemes_with_spacy(
        self, english_g2p_with_spacy, phoneme_backend
    ):
        """Test contractions are phonemized correctly with spaCy.

        spaCy splits contractions (e.g., I've -> I + 've), but our merge
        function should combine them back for proper lexicon lookup.
        """
        test_cases = [
            ("I've learned", "ˌIv lˈɜɹnd"),
            ("We've worked", "wˌiv wˈɜɹkt"),
            ("You're welcome", "jˌʊɹ wˈɛlkəm"),
            ("They're here", "ðˌɛɹ hˈɪɹ"),
        ]
        for text, expected in test_cases:
            result = phonemize_with_backend(
                phoneme_backend, english_g2p_with_spacy, text
            )
            assert (
                result == expected
            ), f"'{text}': expected '{expected}', got '{result}'"


@pytest.mark.espeak
@pytest.mark.spacy
class TestEnglishG2PFull:
    """Tests for fully-featured EnglishG2P."""

    def test_full_sentence(self, english_g2p_full):
        """Test full sentence processing."""
        tokens = english_g2p_full("The quick brown fox jumps over the lazy dog.")
        assert len(tokens) > 0
        # All word tokens should have phonemes
        for token in tokens:
            if token.is_word:
                assert token.phonemes is not None
                assert token.phonemes != ""

    def test_context_dependent_pronunciation(self, english_g2p_full):
        """Test context-dependent pronunciations."""
        # "the" before vowel vs consonant
        tokens_vowel = english_g2p_full("the apple")
        tokens_consonant = english_g2p_full("the book")

        the_vowel = [t for t in tokens_vowel if t.text.lower() == "the"][0]
        the_consonant = [t for t in tokens_consonant if t.text.lower() == "the"][0]

        # They might be different (ði vs ðə)
        # This tests the context mechanism is working
        assert the_vowel.phonemes is not None
        assert the_consonant.phonemes is not None


class TestEnglishG2PTokenization:
    """Tests for tokenization in EnglishG2P."""

    def test_simple_tokenization(self, english_g2p_no_espeak):
        """Test simple tokenization without spaCy."""
        tokens = english_g2p_no_espeak("hello world")
        texts = [t.text for t in tokens]
        assert "hello" in texts
        assert "world" in texts

    def test_punctuation_tokenization(self, english_g2p_no_espeak):
        """Test punctuation tokenization."""
        tokens = english_g2p_no_espeak("Hello, world!")
        texts = [t.text for t in tokens]
        assert "Hello" in texts
        assert "," in texts
        assert "world" in texts
        assert "!" in texts

    def test_whitespace_handling(self, english_g2p_no_espeak):
        """Test whitespace is captured in tokens."""
        tokens = english_g2p_no_espeak("hello world")
        # First token should have trailing whitespace
        assert tokens[0].whitespace == " " or any(t.whitespace for t in tokens)

    def test_contraction_tokenization(self, english_g2p_no_espeak):
        """Test contractions are tokenized as single tokens."""
        # Test various contractions
        contractions = ["I've", "we've", "you've", "they've", "don't", "won't", "can't"]
        for contraction in contractions:
            tokens = english_g2p_no_espeak(contraction)
            # Should be a single token (not split by apostrophe)
            word_tokens = [t for t in tokens if t.text == contraction]
            assert len(word_tokens) == 1, f"'{contraction}' should be a single token"

    def test_contraction_phonemes(self, english_g2p_no_espeak):
        """Test contractions have correct phonemes."""
        # Test that contractions get proper phonemes from the lexicon
        # Note: Capitalized forms may have different stress patterns
        test_cases = [
            ("I've", "ˌIv"),
            ("we've", "wiv"),  # lowercase has no secondary stress
            ("We've", "wˌiv"),  # capitalized has secondary stress
            ("you've", "juv"),
            ("they've", "ðAv"),
            ("don't", "dˈOnt"),
            ("won't", "wˈOnt"),
            ("can't", "kˈænt"),
            ("he's", "hiz"),
            ("she's", "ʃiz"),
            ("it's", "ɪts"),
        ]
        for word, expected_phonemes in test_cases:
            tokens = english_g2p_no_espeak(word)
            assert len(tokens) >= 1, f"Should have token for '{word}'"
            actual = tokens[0].phonemes
            assert (
                actual == expected_phonemes
            ), f"'{word}': expected '{expected_phonemes}', got '{actual}'"

    def test_contraction_in_sentence(self, english_g2p_no_espeak):
        """Test contractions work correctly within sentences."""
        # Test "I've learned"
        tokens = english_g2p_no_espeak("I've learned")
        texts = [t.text for t in tokens]
        assert "I've" in texts, "I've should be a single token"

        # Check phonemes
        ive_token = [t for t in tokens if t.text == "I've"][0]
        assert ive_token.phonemes == "ˌIv", f"I've phonemes: {ive_token.phonemes}"

        # Test "We've worked"
        tokens = english_g2p_no_espeak("We've worked")
        texts = [t.text for t in tokens]
        assert "We've" in texts, "We've should be a single token"

        weve_token = [t for t in tokens if t.text == "We've"][0]
        assert weve_token.phonemes == "wˌiv", f"We've phonemes: {weve_token.phonemes}"


class TestMainAPI:
    """Tests for the main kokorog2p API."""

    def test_import_main_api(self):
        """Test importing main API."""
        from kokorog2p import get_g2p, phonemize, tokenize

        assert callable(phonemize)
        assert callable(tokenize)
        assert callable(get_g2p)

    def test_get_g2p_caching(self):
        """Test G2P instances are cached."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p1 = get_g2p("en-us", use_espeak_fallback=False, use_spacy=False)
        g2p2 = get_g2p("en-us", use_espeak_fallback=False, use_spacy=False)
        assert g2p1 is g2p2

        # Different options should create different instances
        get_g2p("en-us", use_espeak_fallback=True, use_spacy=False)
        # Note: Can't test this without espeak, but the cache key is different

    def test_get_g2p_cache_includes_kwargs(self):
        """Test kwargs are included in get_g2p cache key."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p_default = get_g2p("en-us", use_spacy=False)
        g2p_no_context = get_g2p(
            "en-us",
            use_spacy=False,
            enable_context_detection=False,
        )
        assert g2p_default is not g2p_no_context

        g2p_unk = get_g2p("en-us", use_spacy=False, unk="?")
        assert g2p_default is not g2p_unk

    def test_get_g2p_unsupported_language(self):
        """Test unsupported language falls back to EspeakOnlyG2P."""
        from kokorog2p import clear_cache, get_g2p
        from kokorog2p.espeak_g2p import EspeakOnlyG2P

        clear_cache()
        g2p = get_g2p("sw-sw", backend="espeak")  # Swahili - not yet implemented
        assert isinstance(g2p, EspeakOnlyG2P)

    def test_clear_cache(self):
        """Test cache clearing."""
        from kokorog2p import clear_cache, get_g2p

        g2p1 = get_g2p("en-us", use_espeak_fallback=False, use_spacy=False)
        clear_cache()
        g2p2 = get_g2p("en-us", use_espeak_fallback=False, use_spacy=False)
        # After clearing, should be a new instance
        assert g2p1 is not g2p2

    def test_phonemize_function(self):
        """Test phonemize convenience function."""
        from kokorog2p import phonemize

        result = phonemize("hello", use_espeak_fallback=False, use_spacy=False)
        assert isinstance(result.phonemes, str)
        assert len(result.phonemes) > 0

    def test_tokenize_function(self):
        """Test tokenize convenience function."""
        from kokorog2p import TokenSpan, tokenize

        tokens = tokenize("hello world")
        assert isinstance(tokens, list)
        assert all(isinstance(t, TokenSpan) for t in tokens)

    def test_version_available(self):
        """Test version is available."""
        from kokorog2p import __version__

        assert isinstance(__version__, str)


@pytest.mark.spacy
class TestEnNormalization:
    """Comprehensive tests for normalization handling with spaCy."""

    @pytest.fixture
    def g2p_spacy(self):
        """Create an EnglishG2P instance with spaCy enabled."""
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(language="en-us", use_spacy=True, use_espeak_fallback=False)

    def test_en_ellipses(self, g2p_spacy):
        """Test 'don't' is phonemized as a single word, not 'do' + 'n't'."""
        tokens = g2p_spacy("Don't . . . worry.")

        # Should have 2 word tokens (Don't, worry)
        word_tokens = [t for t in tokens if t.text not in (" ", ".")]
        assert len(word_tokens) == 3
        assert word_tokens[0].text == "Don't"
        assert word_tokens[0].phonemes == "dˈOnt"
        assert word_tokens[1].text == "…"
        assert word_tokens[1].phonemes == "…"


@pytest.mark.spacy
class TestContractionMerging:
    """Comprehensive tests for contraction handling with spaCy.

    These tests ensure that spaCy-split contractions (e.g., "Don't" -> "Do" + "n't")
    are properly merged back together for correct lexicon lookup and phonemization.

    This addresses the issue where contractions were being incorrectly phonemized
    as separate words instead of using their dictionary entries.
    """

    @pytest.fixture
    def g2p_spacy(self):
        """Create an EnglishG2P instance with spaCy enabled."""
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(language="en-us", use_spacy=True, use_espeak_fallback=False)

    def test_dont_contraction(self, g2p_spacy):
        """Test 'don't' is phonemized as a single word, not 'do' + 'n't'."""
        tokens = g2p_spacy("Don't worry")

        # Should have 2 word tokens (Don't, worry)
        word_tokens = [t for t in tokens if t.text not in (" ", ".")]
        assert len(word_tokens) == 2
        assert word_tokens[0].text == "Don't"
        assert word_tokens[0].phonemes == "dˈOnt"

    def test_cant_contraction(self, g2p_spacy):
        """Test 'can't' is phonemized correctly."""
        tokens = g2p_spacy("I can't believe it")

        cant_token = [t for t in tokens if t.text == "can't"][0]
        assert cant_token.phonemes == "kˈænt"

    def test_wont_contraction(self, g2p_spacy):
        """Test 'won't' is phonemized correctly."""
        tokens = g2p_spacy("I won't go")

        wont_token = [t for t in tokens if t.text == "won't"][0]
        assert wont_token.phonemes == "wOnt"

    def test_ive_contraction(self, g2p_spacy):
        """Test 'I've' is phonemized as a single word."""
        tokens = g2p_spacy("I've done it")

        ive_token = [t for t in tokens if t.text == "I've"][0]
        assert ive_token.phonemes == "ˌIv"

    def test_weve_contraction(self, g2p_spacy):
        """Test 'we've' is phonemized correctly."""
        tokens = g2p_spacy("We've finished")

        weve_token = [t for t in tokens if t.text == "We've"][0]
        assert weve_token.phonemes == "wˌiv"

    def test_youre_contraction(self, g2p_spacy):
        """Test 'you're' is phonemized correctly."""
        tokens = g2p_spacy("You're welcome")

        youre_token = [t for t in tokens if t.text == "You're"][0]
        assert youre_token.phonemes == "jˌʊɹ"

    def test_theyre_contraction(self, g2p_spacy):
        """Test 'they're' is phonemized correctly."""
        tokens = g2p_spacy("They're here")

        theyre_token = [t for t in tokens if t.text == "They're"][0]
        assert theyre_token.phonemes == "ðˌɛɹ"

    def test_ill_contraction(self, g2p_spacy):
        """Test 'I'll' is phonemized correctly."""
        tokens = g2p_spacy("I'll help")

        ill_token = [t for t in tokens if t.text == "I'll"][0]
        assert ill_token.phonemes == "ˌIl"

    def test_youll_contraction(self, g2p_spacy):
        """Test 'you'll' is phonemized correctly."""
        tokens = g2p_spacy("You'll see")

        youll_token = [t for t in tokens if t.text == "You'll"][0]
        assert youll_token.phonemes == "jˌul"

    def test_id_contraction(self, g2p_spacy):
        """Test 'I'd' is phonemized correctly."""
        tokens = g2p_spacy("I'd like that")

        id_token = [t for t in tokens if t.text == "I'd"][0]
        assert id_token.phonemes == "ˌId"

    def test_youd_contraction(self, g2p_spacy):
        """Test 'you'd' is phonemized correctly."""
        tokens = g2p_spacy("You'd better hurry")

        youd_token = [t for t in tokens if t.text == "You'd"][0]
        assert youd_token.phonemes == "jˌud"

    def test_shes_contraction(self, g2p_spacy):
        """Test 'she's' is phonemized correctly."""
        tokens = g2p_spacy("She's here")

        shes_token = [t for t in tokens if t.text == "She's"][0]
        assert shes_token.phonemes == "ʃˌiz"

    def test_hes_contraction(self, g2p_spacy):
        """Test 'he's' is phonemized correctly."""
        tokens = g2p_spacy("He's coming")

        hes_token = [t for t in tokens if t.text == "He's"][0]
        assert hes_token.phonemes == "hˌiz"

    def test_its_contraction(self, g2p_spacy):
        """Test 'it's' is phonemized correctly."""
        tokens = g2p_spacy("It's ready")

        its_token = [t for t in tokens if t.text == "It's"][0]
        assert its_token.phonemes == "ˌɪts"

    def test_lets_contraction(self, g2p_spacy):
        """Test 'let's' is phonemized correctly."""
        tokens = g2p_spacy("Let's go")

        lets_token = [t for t in tokens if t.text == "Let's"][0]
        assert lets_token.phonemes == "lˈɛts"

    def test_thats_contraction(self, g2p_spacy):
        """Test 'that's' is phonemized correctly."""
        tokens = g2p_spacy("That's correct")

        thats_token = [t for t in tokens if t.text == "That's"][0]
        assert thats_token.phonemes == "ðˈæts"

    def test_multiple_contractions_in_sentence(self, g2p_spacy):
        """Test multiple contractions in one sentence."""
        text = "I don't think they're ready, but we'll see."
        tokens = g2p_spacy(text)

        word_tokens = {
            t.text: t
            for t in tokens
            if t.text.replace("'", "").isalpha() or "'" in t.text
        }

        assert word_tokens["don't"].phonemes == "dˈOnt"
        assert word_tokens["they're"].phonemes == "ðɛɹ"
        assert word_tokens["we'll"].phonemes == "wil"

    def test_contraction_case_insensitive(self, g2p_spacy):
        """Test contractions work regardless of case."""
        # Test uppercase
        tokens_upper = g2p_spacy("DON'T SHOUT")
        dont_upper = [t for t in tokens_upper if "don't" in t.text.lower()][0]

        # Test lowercase
        tokens_lower = g2p_spacy("don't shout")
        dont_lower = [t for t in tokens_lower if t.text == "don't"][0]

        # Should have same phonemes (case normalized in lookup)
        assert dont_upper.phonemes == dont_lower.phonemes

    def test_contraction_tokenization_count(self, g2p_spacy):
        """Test that contractions are counted as single tokens, not split."""
        tokens = g2p_spacy("I've can't won't don't")

        # Should have 4 word tokens, not 8
        word_tokens = [t for t in tokens if t.text.strip() and not t.phonemes == " "]
        assert len(word_tokens) == 4

    def test_possessive_vs_contraction(self, g2p_spacy):
        """Test that 's can be either possessive or contraction."""
        # Contraction: "he is"
        tokens1 = g2p_spacy("He's tall")
        hes_token = [t for t in tokens1 if t.text == "He's"][0]
        assert hes_token.phonemes == "hˌiz"

        # Note: Possessives like "John's" would be handled differently
        # This test just ensures 's contractions work

    def test_contraction_with_punctuation(self, g2p_spacy):
        """Test contractions followed by punctuation."""
        tokens = g2p_spacy("Don't! Can't? Won't.")

        dont_token = [t for t in tokens if t.text == "Don't"][0]
        cant_token = [t for t in tokens if t.text == "Can't"][0]
        wont_token = [t for t in tokens if t.text == "Won't"][0]

        assert dont_token.phonemes == "dˈOnt"
        assert cant_token.phonemes == "kˈænt"
        assert wont_token.phonemes == "wˈOnt"

    def test_phonemize_with_contractions(self, g2p_spacy, phoneme_backend):
        """Test the phonemize() method with contractions."""
        result = phonemize_with_backend(phoneme_backend, g2p_spacy, "I don't think so")

        # Should contain the correct phoneme for "don't"
        assert "dˈOnt" in result

        # Should not contain separate "do" phoneme
        assert result.count("dˈu") == 0  # "do" should not appear separately


@pytest.mark.spacy
class TestDoubleContractions:
    """Tests for double contractions like "could've", "I'd've", etc.

    These test that the contraction merging handles chains of contractions
    where spaCy splits them into 3+ tokens (e.g., "I'd've" -> "I" + "'d" + "'ve").
    """

    @pytest.fixture
    def g2p_spacy(self):
        """Create an EnglishG2P instance with spaCy enabled."""
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(language="en-us", use_spacy=True, use_espeak_fallback=False)

    def test_couldve_tokenization(self, g2p_spacy):
        """Test 'could've' is treated as a single token."""
        tokens = g2p_spacy("I could've done it")

        # Find the could've token
        couldve_token = [t for t in tokens if t.text == "could've"][0]

        # Should be merged as one token
        assert couldve_token.text == "could've"
        assert couldve_token.phonemes == "kʊdəv"

    def test_shouldve_tokenization(self, g2p_spacy):
        """Test 'should've' is treated as a single token."""
        tokens = g2p_spacy("You should've known")

        # Find the should've token
        shouldve_tokens = [t for t in tokens if "should've" in t.text]
        assert len(shouldve_tokens) == 1
        assert shouldve_tokens[0].text == "should've"

    def test_wouldve_tokenization(self, g2p_spacy):
        """Test 'would've' is treated as a single token."""
        tokens = g2p_spacy("I would've tried")

        # Find the would've token
        wouldve_tokens = [t for t in tokens if "would've" in t.text]
        assert len(wouldve_tokens) == 1
        assert wouldve_tokens[0].text == "would've"

    def test_idve_tokenization(self, g2p_spacy):
        """Test 'I'd've' is treated as a single token."""
        tokens = g2p_spacy("I'd've helped")

        # Find the I'd've token
        idve_tokens = [t for t in tokens if "I'd've" in t.text]
        assert len(idve_tokens) == 1
        assert idve_tokens[0].text == "I'd've"

    def test_youdve_tokenization(self, g2p_spacy):
        """Test 'you'd've' is treated as a single token."""
        tokens = g2p_spacy("You'd've loved it")

        # Find the you'd've token
        youdve_tokens = [t for t in tokens if "you'd've" in t.text.lower()]
        assert len(youdve_tokens) == 1
        assert youdve_tokens[0].text == "You'd've"

    def test_theydve_tokenization(self, g2p_spacy):
        """Test 'they'd've' is treated as a single token."""
        tokens = g2p_spacy("They'd've been there")

        # Find the they'd've token
        theydve_tokens = [t for t in tokens if "they'd've" in t.text.lower()]
        assert len(theydve_tokens) == 1
        assert theydve_tokens[0].text == "They'd've"

    def test_couldntve_tokenization(self, g2p_spacy):
        """Test 'couldn't've' is treated as a single token."""
        tokens = g2p_spacy("I couldn't've done better")

        # Find the couldn't've token
        couldntve_tokens = [t for t in tokens if "couldn't've" in t.text.lower()]
        assert len(couldntve_tokens) == 1
        assert couldntve_tokens[0].text == "couldn't've"

    def test_shouldntve_tokenization(self, g2p_spacy):
        """Test 'shouldn't've' is treated as a single token."""
        tokens = g2p_spacy("You shouldn't've said that")

        # Find the shouldn't've token
        shouldntve_tokens = [t for t in tokens if "shouldn't've" in t.text.lower()]
        assert len(shouldntve_tokens) == 1
        assert shouldntve_tokens[0].text == "shouldn't've"

    def test_wouldntve_tokenization(self, g2p_spacy):
        """Test 'wouldn't've' is treated as a single token."""
        tokens = g2p_spacy("I wouldn't've believed it")

        # Find the wouldn't've token
        wouldntve_tokens = [t for t in tokens if "wouldn't've" in t.text.lower()]
        assert len(wouldntve_tokens) == 1
        assert wouldntve_tokens[0].text == "wouldn't've"

    def test_couldve_phonemes(self, g2p_spacy):
        """Test 'could've' has correct phonemes from lexicon."""
        tokens = g2p_spacy("could've")
        assert tokens[0].phonemes == "kˈʊdəv"

    def test_double_contraction_not_split(self, g2p_spacy):
        """Test that double contractions aren't split into multiple word tokens."""
        text = "I could've should've would've"
        tokens = g2p_spacy(text)

        # Count word tokens (excluding punctuation and whitespace)
        word_tokens = [t for t in tokens if t.text.strip() and "'" in t.text]

        # Should have exactly 3 contraction tokens, not 6 or more
        assert len(word_tokens) == 3
        assert word_tokens[0].text == "could've"
        assert word_tokens[1].text == "should've"
        assert word_tokens[2].text == "would've"

    def test_triple_contraction_chain(self, g2p_spacy):
        """Test merging works even with 3 apostrophe parts."""
        # "I'd've" is actually I + 'd + 've (3 parts)
        tokens = g2p_spacy("I'd've")

        # Should result in single token
        word_tokens = [t for t in tokens if t.text.strip()]
        assert len(word_tokens) == 1
        assert word_tokens[0].text == "I'd've"

    def test_mixed_single_and_double_contractions(self, g2p_spacy):
        """Test sentence with both single and double contractions."""
        text = "I don't think I could've done it, but you're right"
        tokens = g2p_spacy(text)

        contractions = {t.text: t for t in tokens if "'" in t.text}

        # All contractions should be merged correctly
        assert "don't" in contractions
        assert "could've" in contractions
        assert "you're" in contractions

        # Verify they're single tokens
        assert len([t for t in tokens if t.text == "don't"]) == 1
        assert len([t for t in tokens if t.text == "could've"]) == 1
        assert len([t for t in tokens if t.text == "you're"]) == 1

    def test_double_contraction_with_punctuation(self, g2p_spacy):
        """Test double contractions work with punctuation."""
        tokens = g2p_spacy("I could've!")

        couldve_token = [t for t in tokens if "could've" in t.text][0]
        assert couldve_token.text == "could've"
        assert couldve_token.phonemes == "kˈʊdəv"

    def test_double_contraction_case_variations(self, g2p_spacy):
        """Test double contractions work with different cases."""
        test_cases = [
            "could've",
            "Could've",
            "COULD'VE",
        ]

        for text in test_cases:
            tokens = g2p_spacy(text)
            # Should be single token regardless of case
            word_tokens = [t for t in tokens if t.text.strip()]
            assert len(word_tokens) == 1
            assert "could" in word_tokens[0].text.lower()
            assert "ve" in word_tokens[0].text.lower()


@pytest.mark.spacy
class TestContractionRobustness:
    """Tests for robust contraction handling.

    These tests validate that the lexicon-aware pre-tokenization approach
    correctly handles contractions with various apostrophe characters and
    prevents spaCy from splitting them incorrectly.
    """

    @pytest.fixture
    def g2p_spacy(self):
        """Create an EnglishG2P instance with spaCy enabled."""
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(language="en-us", use_spacy=True)

    def test_dont_with_straight_apostrophe(self, g2p_spacy, phoneme_backend):
        """Test 'don't' with straight apostrophe (U+0027)."""
        text = "I don't understand them, but I love them."
        result = phonemize_with_backend(phoneme_backend, g2p_spacy, text)

        # Should contain correct phoneme for don't
        assert "dˈOnt" in result

        # Should NOT contain the bug signature (split don't)
        assert "dˈu" not in result or "ˈɛnt" not in result

        # Verify token is intact
        tokens = g2p_spacy(text)
        dont_tokens = [t for t in tokens if "don't" in t.text.lower()]
        assert len(dont_tokens) == 1
        assert dont_tokens[0].text == "don't"
        assert dont_tokens[0].phonemes == "dˈOnt"

    def test_dont_with_curly_apostrophe(self, g2p_spacy, phoneme_backend):
        """Test 'don't' with right single quotation mark (U+2019)."""
        text = "I don't understand"
        result = phonemize_with_backend(phoneme_backend, g2p_spacy, text)

        # Should be normalized and phonemized correctly
        assert "dˈOnt" in result

        # Token should be normalized to straight apostrophe
        tokens = g2p_spacy(text)
        dont_tokens = [t for t in tokens if "don" in t.text.lower() and "'" in t.text]
        assert len(dont_tokens) == 1
        assert dont_tokens[0].phonemes == "dˈOnt"

    def test_dont_with_grave_accent(self, g2p_spacy, phoneme_backend):
        """Test 'don't' with grave accent (U+0060) - common typo."""
        text = "I don`t understand"
        result = phonemize_with_backend(phoneme_backend, g2p_spacy, text)

        # Should be normalized to apostrophe and phonemized correctly
        assert "dˈOnt" in result

        # Should NOT have separate "don" and "t" tokens
        tokens = g2p_spacy(text)
        word_texts = [t.text for t in tokens if t.is_word]
        assert "don" not in word_texts  # Should be "don't", not "don"

    def test_dont_with_acute_accent(self, g2p_spacy, phoneme_backend):
        """Test 'don't' with acute accent (U+00B4) - another typo."""
        text = "I don´t understand"
        result = phonemize_with_backend(phoneme_backend, g2p_spacy, text)

        # Should be normalized and phonemized correctly
        assert "dˈOnt" in result

    def test_multiple_apostrophe_types_mixed(self, g2p_spacy, phoneme_backend):
        """Test text with multiple different apostrophe types."""
        # Mix straight, curly, and grave apostrophes
        text = "I don't think you're right, but we`ve tried."
        result = phonemize_with_backend(phoneme_backend, g2p_spacy, text)

        # All contractions should work correctly
        assert "dˈOnt" in result  # don't
        assert "jˌʊɹ" in result or "jʊɹ" in result  # you're (with or without stress)
        assert "wiv" in result or "wˌiv" in result  # we've

    def test_contraction_prevents_split_phonemization(self, g2p_spacy):
        """Test that contractions in lexicon are NOT split by spaCy."""
        text = "don't can't won't"
        tokens = g2p_spacy(text)

        word_tokens = [t for t in tokens if t.is_word]

        # Should be exactly 3 tokens, not 6
        assert len(word_tokens) == 3

        # Each should be a complete contraction
        assert word_tokens[0].text == "don't"
        assert word_tokens[1].text == "can't"
        assert word_tokens[2].text == "won't"

        # Each should have correct phonemes from lexicon
        assert word_tokens[0].phonemes == "dˈOnt"
        assert word_tokens[1].phonemes == "kˈænt"
        assert word_tokens[2].phonemes == "wˈOnt"  # Note: has stress marker

    def test_contraction_with_case_variations(self, g2p_spacy):
        """Test contractions work with different case variations."""
        test_cases = [
            ("I don't know", "dˈOnt"),
            ("I Don't know", "dˈOnt"),
            ("I DON'T know", "dˈOnt"),
        ]

        for text, expected_phoneme in test_cases:
            tokens = g2p_spacy(text)
            # Find the don't token
            dont_tokens = [
                t for t in tokens if "don" in t.text.lower() and "'" in t.text
            ]
            assert len(dont_tokens) == 1
            assert dont_tokens[0].phonemes == expected_phoneme

    def test_user_reported_sentence(self, g2p_spacy, phoneme_backend):
        """Test the exact sentence reported by user that was failing."""
        text = "I don't understand them, but I love them."
        result = phonemize_with_backend(phoneme_backend, g2p_spacy, text)

        # Expected output
        expected_dont = "dˈOnt"

        # Should have correct phoneme
        assert expected_dont in result

        # Should NOT have the bug the user reported
        bug_signature = 'dˈɑn"tˈi'
        assert bug_signature not in result

        # Alternative bug signature (split tokens)
        assert not ("dˈu" in result and "ˈɛnt" in result)

    def test_informal_contractions(self, g2p_spacy):
        """Test that informal contractions are not split by spaCy.

        Informal contractions like "gonna", "gotta", "wanna" should be
        treated as single tokens and phonemized using their lexicon entries,
        not split into separate parts.

        Regression test for: "Gonna try." being split into "Gon" + "na"
        """
        # Test cases: (text, word, expected_phoneme)
        test_cases = [
            ("Gonna try.", "gonna", "ɡˈʌnə"),
            ("I wanna go.", "wanna", "wˈɑnə"),
            ("Gotta run.", "gotta", "ɡˈɑɾə"),
            ("It's kinda nice.", "kinda", "kˈIndə"),
            ("Sorta cool.", "sorta", "sˈɔɹɾə"),
            ("Get outta here.", "outta", "ˈWɾə"),
            ("Lemme see.", "lemme", "lˈɛmi"),
            ("Gimme that.", "gimme", "ɡˈɪmi"),
            ("I dunno.", "dunno", "dənˈO"),
        ]

        for text, word, expected_phoneme in test_cases:
            tokens = g2p_spacy(text)

            # Find the informal contraction token
            # Check both lowercase and capitalized versions
            word_tokens = [t for t in tokens if t.text.lower() == word.lower()]

            assert len(word_tokens) == 1, (
                f"Expected 1 '{word}' token in {repr(text)}, "
                f"found {len(word_tokens)}. "
                f"Tokens: {[t.text for t in tokens if t.is_word]}"
            )

            # Check it has correct phonemes from lexicon
            actual_phoneme = word_tokens[0].phonemes
            assert actual_phoneme == expected_phoneme, (
                f"For '{word}' in {repr(text)}: "
                f"expected '{expected_phoneme}', got '{actual_phoneme}'"
            )

            # Verify it wasn't split
            word_texts = [t.text.lower() for t in tokens if t.is_word]
            # Common split patterns
            if word == "gonna":
                assert (
                    "gon" not in word_texts
                ), f"'{word}' was split into parts: {word_texts}"
            elif word == "gotta":
                assert (
                    "got" not in word_texts
                ), f"'{word}' was split into parts: {word_texts}"

    def test_dont_in_quoted_dialogue(self, g2p_spacy, phoneme_backend):
        """Test 'don't' in quoted dialogue with punctuation.

        Regression test for: 'I don't mind at all,' said Totho.
        The contraction should not be split by spaCy.
        Tests various quote characters commonly used in ebooks.
        """
        # Test with various quote characters used in ebooks
        test_cases = [
            "'I don't mind at all,' said Totho.",  # Straight quotes
            # Curly single quotes (U+2018/U+2019)
            "\u2018I don\u2019t mind at all,\u2019 said Totho.",
            '"I don\'t mind at all," said Totho.',  # Straight double quotes
            # Curly double quotes (U+201C/U+201D)
            "\u201cI don\u2019t mind at all,\u201d said Totho.",
            # Single guillemets (U+2039/U+203A)
            "\u2039I don\u2019t mind at all,\u203a said Totho.",
            # Double guillemets (U+00AB/U+00BB)
            "\u00abI don\u2019t mind at all,\u00bb said Totho.",
        ]

        for text in test_cases:
            tokens = g2p_spacy(text)

            # Find the don't token
            dont_tokens = [t for t in tokens if "don't" == t.text]
            assert (
                len(dont_tokens) == 1
            ), f"Expected 1 'don't' token in {repr(text)}, found {len(dont_tokens)}"

            # Should have correct phonemes
            assert (
                dont_tokens[0].phonemes == "dˈOnt"
            ), f"Expected 'dˈOnt', got '{dont_tokens[0].phonemes}' in {repr(text)}"

            # Verify the full phonemized result
            result = phonemize_with_backend(phoneme_backend, g2p_spacy, text)
            assert (
                "dˈOnt" in result
            ), f"Expected 'dˈOnt' in result for {repr(text)}, got: {result}"

            # Should NOT be split into separate tokens
            word_texts = [t.text for t in tokens if t.is_word]
            assert (
                "don't" in word_texts
            ), f"'don't' not found in {word_texts} for {repr(text)}"
            # Should not have separate "do"
            do_count = word_texts.count("do")
            assert do_count == 0, (
                f"Found {do_count} 'do' tokens (should be 0) "
                f"in {word_texts} for {repr(text)}"
            )


class TestGoruutFallback:
    """Test goruut fallback functionality for English G2P."""

    @pytest.fixture
    def g2p_goruut(self):
        """Create EnglishG2P with goruut fallback."""
        pytest.importorskip("pygoruut")
        return EnglishG2P(
            use_espeak_fallback=False,
            use_goruut_fallback=True,
            load_gold=False,
            load_silver=False,
        )

    @pytest.fixture
    def g2p_espeak(self):
        """Create EnglishG2P with espeak fallback for comparison."""
        return EnglishG2P(
            use_espeak_fallback=True,
            use_goruut_fallback=False,
            load_gold=False,
            load_silver=False,
        )

    def test_mutual_exclusion_error(self):
        """Test that both fallbacks can't be enabled simultaneously."""
        with pytest.raises(ValueError, match="Cannot use both"):
            EnglishG2P(use_espeak_fallback=True, use_goruut_fallback=True)

    def test_goruut_fallback_basic(self, g2p_goruut, phoneme_backend):
        """Test basic goruut fallback for unknown words."""
        # Use a made-up word not in dictionary
        result = phonemize_with_backend(phoneme_backend, g2p_goruut, "xyzabc")

        # Should produce some phonemes (not empty or unknown marker)
        assert result
        assert result != "❓"
        assert len(result) > 0

    def test_goruut_fallback_produces_phonemes(self, g2p_goruut, phoneme_backend):
        """Test that goruut produces valid phonemes for common words."""
        result = phonemize_with_backend(phoneme_backend, g2p_goruut, "hello")

        # Should contain recognizable IPA characters
        assert any(c in result for c in "həɛlˈO")
        assert result != "❓"

    def test_goruut_vs_espeak_both_work(self, g2p_goruut, g2p_espeak, phoneme_backend):
        """Test that both goruut and espeak produce phonemes (may differ)."""
        word = "supercalifragilisticexpialidocious"

        result_goruut = phonemize_with_backend(phoneme_backend, g2p_goruut, word)
        result_espeak = phonemize_with_backend(phoneme_backend, g2p_espeak, word)

        # Both should produce something
        assert result_goruut
        assert result_espeak

        # Both should be non-trivial (not just unknown markers)
        assert len(result_goruut) > 5
        assert len(result_espeak) > 5

    def test_no_fallback_returns_unknown(self, phoneme_backend):
        """Test that without fallback, unknown words return unknown marker."""
        g2p_none = EnglishG2P(
            use_espeak_fallback=False,
            use_goruut_fallback=False,
            load_gold=False,
            load_silver=False,
        )

        result = phonemize_with_backend(phoneme_backend, g2p_none, "xyzabc")

        # Should contain unknown marker
        assert "❓" in result

    def test_goruut_fallback_with_real_words(self, g2p_goruut, phoneme_backend):
        """Test goruut fallback with various real English words."""
        words = ["test", "world", "python", "programming"]

        for word in words:
            result = phonemize_with_backend(phoneme_backend, g2p_goruut, word)
            # Should produce phonemes, not unknown marker
            assert result
            assert "❓" not in result

    def test_goruut_british_variant(self, phoneme_backend):
        """Test goruut fallback with British English."""
        pytest.importorskip("pygoruut")

        g2p_gb = EnglishG2P(
            language="en-gb",
            use_espeak_fallback=False,
            use_goruut_fallback=True,
            load_gold=False,
            load_silver=False,
        )

        result = phonemize_with_backend(phoneme_backend, g2p_gb, "hello")

        # Should produce phonemes
        assert result
        assert result != "❓"

    def test_goruut_fallback_initialization(self, g2p_goruut):
        """Test that goruut fallback is properly initialized."""
        # Fallback should exist
        assert g2p_goruut.fallback is not None

        # Should be GoruutFallback instance
        from kokorog2p.en.fallback import GoruutFallback

        assert isinstance(g2p_goruut.fallback, GoruutFallback)

    def test_goruut_sentence_phonemization(self, g2p_goruut, phoneme_backend):
        """Test goruut fallback with full sentences."""
        text = "The quick brown fox jumps over the lazy dog."
        result = phonemize_with_backend(phoneme_backend, g2p_goruut, text)

        # Should produce substantial output
        assert len(result) > 20
        assert "❓" not in result
