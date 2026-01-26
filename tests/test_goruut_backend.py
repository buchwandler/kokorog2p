"""Tests for the goruut backend."""

import pytest

# Check if pygoruut is available
try:
    from kokorog2p.backends.goruut import GoruutBackend

    HAS_GORUUT = GoruutBackend.is_available()
except ImportError:
    HAS_GORUUT = False


pytestmark = pytest.mark.skipif(not HAS_GORUUT, reason="pygoruut not installed")


class TestFromGoruut:
    """Tests for the from_goruut conversion function."""

    def test_diphthong_ei(self):
        """Test eɪ -> A conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("sˈeɪ") == "sˈA"
        assert from_goruut("ɹˈeɪsɪŋ") == "ɹˈAsɪŋ"

    def test_diphthong_ai(self):
        """Test aɪ -> I conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("maɪ") == "mI"
        assert from_goruut("nˈaɪn") == "nˈIn"

    def test_diphthong_au(self):
        """Test aʊ -> W conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("nˈaʊ") == "nˈW"
        assert from_goruut("θˈaʊzənd") == "θˈWzənd"

    def test_diphthong_oi(self):
        """Test ɔɪ -> Y conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("bˈɔɪ") == "bˈY"

    def test_diphthong_ou(self):
        """Test oʊ -> O conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("həlˈoʊ") == "həlˈO"
        assert from_goruut("gˈoʊ") == "ɡˈO"

    def test_affricate_tsh(self):
        """Test tʃ -> ʧ conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("tʃˈɜɹtʃ") == "ʧˈɜɹʧ"

    def test_affricate_dzh(self):
        """Test dʒ -> ʤ conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("dʒˈʌdʒ") == "ʤˈʌʤ"

    def test_consonant_g(self):
        """Test g -> ɡ conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("gˈoʊ") == "ɡˈO"

    def test_british_keeps_length(self):
        """Test that British English keeps length marks."""
        from kokorog2p.phonemes import from_goruut

        # British should keep ː
        result = from_goruut("hˈɑːd", british=True)
        assert "ː" in result

    def test_us_removes_length(self):
        """Test that US English removes length marks."""
        from kokorog2p.phonemes import from_goruut

        result = from_goruut("hˈɑːd", british=False)
        assert "ː" not in result


class TestGoruutBackend:
    """Tests for the GoruutBackend class."""

    @pytest.fixture
    def goruut_backend(self):
        """Create a GoruutBackend instance."""
        return GoruutBackend("en-us")

    @pytest.fixture
    def goruut_backend_gb(self):
        """Create a British GoruutBackend instance."""
        return GoruutBackend("en-gb")

    def test_phonemize_word(self, goruut_backend):
        """Test phonemizing a single word."""
        result = goruut_backend.phonemize("hello")
        assert result  # Should return non-empty string
        assert isinstance(result, str)

    def test_phonemize_sentence(self, goruut_backend):
        """Test phonemizing a sentence."""
        result = goruut_backend.phonemize("Hello world")
        assert result
        assert " " in result  # Should have space between words

    def test_phonemize_with_kokoro(self, goruut_backend):
        """Test conversion to Kokoro format."""
        result = goruut_backend.phonemize("say", convert_to_kokoro=True)
        assert "A" in result  # eɪ should be converted to A

    def test_phonemize_raw_ipa(self, goruut_backend):
        """Test getting raw IPA output."""
        result = goruut_backend.phonemize("say", convert_to_kokoro=False)
        assert "eɪ" in result or "e" in result  # Should have raw diphthong

    def test_phonemize_list(self, goruut_backend):
        """Test phonemizing a list of texts."""
        texts = ["hello", "world"]
        results = goruut_backend.phonemize_list(texts)
        assert len(results) == 2
        assert all(isinstance(r, str) for r in results)

    def test_word_phonemes(self, goruut_backend):
        """Test word_phonemes method."""
        result = goruut_backend.word_phonemes("hello")
        assert result
        assert "_" not in result  # Should not have word separators

    def test_is_british(self, goruut_backend, goruut_backend_gb):
        """Test is_british property."""
        assert not goruut_backend.is_british
        assert goruut_backend_gb.is_british

    def test_is_available(self):
        """Test is_available static method."""
        assert GoruutBackend.is_available() is True

    def test_get_supported_languages(self):
        """Test get_supported_languages method."""
        languages = GoruutBackend.get_supported_languages()
        assert isinstance(languages, list)
        assert "en-us" in languages
        assert "en-gb" in languages
        assert "fr" in languages

    def test_empty_text(self, goruut_backend):
        """Test phonemizing empty text."""
        result = goruut_backend.phonemize("")
        assert result == ""

    def test_repr(self, goruut_backend):
        """Test __repr__ method."""
        repr_str = repr(goruut_backend)
        assert "GoruutBackend" in repr_str
        assert "en-us" in repr_str


class TestGoruutOnlyG2P:
    """Tests for the GoruutOnlyG2P class."""

    def test_create_instance(self):
        """Test creating a GoruutOnlyG2P instance."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        assert g2p.language == "en-us"

    def test_call_returns_tokens(self):
        """Test that __call__ returns a list of tokens."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        tokens = g2p("Hello world")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_phonemize(self):
        """Test phonemize method."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        result = g2p.phonemize("Hello world")
        assert isinstance(result, str)
        assert result  # Non-empty

    def test_lookup(self):
        """Test lookup method."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        result = g2p.lookup("hello")
        assert result is not None

    def test_is_available(self):
        """Test is_available static method."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        assert GoruutOnlyG2P.is_available() is True


class TestMainAPIWithGoruutBackend:
    """Tests for the main API with goruut backend."""

    def test_phonemize_with_goruut(self):
        """Test phonemize function with goruut backend."""
        from kokorog2p import phonemize

        result = phonemize("Hello world", backend="goruut")
        assert isinstance(result.phonemes, str)
        assert result  # Non-empty

    def test_get_g2p_with_goruut(self):
        """Test get_g2p function with goruut backend."""
        from kokorog2p import get_g2p

        g2p = get_g2p("en-us", backend="goruut")
        assert "GoruutOnlyG2P" in type(g2p).__name__

    def test_cache_works_with_backend(self):
        """Test that cache distinguishes between backends."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()

        g2p_espeak = get_g2p("en-us", backend="espeak", use_spacy=False)
        g2p_goruut = get_g2p("en-us", backend="goruut")

        # They should be different instances
        assert type(g2p_espeak).__name__ != type(g2p_goruut).__name__

    def test_french_with_goruut(self):
        """Test French language with goruut backend."""
        from kokorog2p import phonemize

        result = phonemize("Bonjour", language="fr", backend="goruut")
        assert isinstance(result.phonemes, str)
        assert result  # Non-empty

    def test_german_with_goruut(self):
        """Test German language with goruut backend."""
        from kokorog2p import phonemize

        result = phonemize("Hallo", language="de", backend="goruut")
        assert isinstance(result.phonemes, str)
        assert result  # Non-empty
