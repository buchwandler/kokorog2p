"""Tests for the Czech G2P module."""

import pytest

from kokorog2p.cs import CzechG2P
from kokorog2p.token import GToken


class TestCzechG2P:
    """Tests for CzechG2P."""

    @pytest.fixture
    def g2p(self):
        """Create a Czech G2P instance."""
        return CzechG2P()

    def test_creation(self, g2p):
        """Test G2P creation."""
        assert g2p.language == "cs-cz"

    def test_call_returns_tokens(self, g2p):
        """Test calling G2P returns list of tokens."""
        tokens = g2p("dobrý den")
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
        result = g2p.phonemize("Praha")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_lookup_method(self, g2p):
        """Test lookup method."""
        ps = g2p.lookup("Praha")
        assert ps is not None
        assert isinstance(ps, str)

    def test_repr(self, g2p):
        """Test string representation."""
        result = repr(g2p)
        assert "CzechG2P" in result
        assert "cs-cz" in result

    # Czech-specific phonological tests

    def test_ch_digraph(self, g2p):
        """Test ch digraph is converted to x."""
        result = g2p.phonemize("chata")
        assert "x" in result

    def test_palatalization_di(self, g2p):
        """Test d+i palatalization."""
        result = g2p.phonemize("díky")
        assert "ɟ" in result

    def test_palatalization_ti(self, g2p):
        """Test t+i palatalization."""
        result = g2p.phonemize("ticho")
        assert "c" in result

    def test_palatalization_ni(self, g2p):
        """Test n+i palatalization."""
        result = g2p.phonemize("nic")
        assert "ɲ" in result

    def test_me_combination(self, g2p):
        """Test mě combination."""
        result = g2p.phonemize("město")
        assert "mɲɛ" in result

    def test_be_combination(self, g2p):
        """Test bě combination."""
        result = g2p.phonemize("běh")
        assert "bjɛ" in result

    def test_long_vowels(self, g2p):
        """Test long vowel markers."""
        result = g2p.phonemize("máma")
        assert "aː" in result

    def test_r_hacek(self, g2p):
        """Test ř phoneme."""
        result = g2p.phonemize("řeka")
        assert "r̝" in result

    def test_voicing_assimilation(self, g2p):
        """Test voicing assimilation."""
        # Voiced before unvoiced should devoice
        result = g2p.phonemize("odzbrojit")
        # "dz" should become voiced "d͡z" before "b"
        assert "d͡z" in result

    def test_final_devoicing(self, g2p):
        """Test final devoicing."""
        # Final voiced consonants should devoice
        result = g2p.phonemize("led")
        # Final "d" should become "t"
        assert result.endswith("t")

    def test_ts_combination(self, g2p):
        """Test ts combination."""
        result = g2p.phonemize("tsar")
        assert "t͡s" in result

    def test_ie_ia_io_combinations(self, g2p):
        """Test ie/ia/io combinations."""
        result_ie = g2p.phonemize("filosofie")
        assert "ɪjɛ" in result_ie

        result_ia = g2p.phonemize("nokia")
        assert "ɪja" in result_ia

        result_io = g2p.phonemize("rio")
        assert "ɪjo" in result_io

    def test_sentence_with_punctuation(self, g2p):
        """Test sentence with punctuation."""
        tokens = g2p("Jak se máte?")
        texts = [t.text for t in tokens]
        assert "Jak" in texts
        assert "?" in texts

    def test_known_words(self, g2p):
        """Test known Czech words have correct phonemes."""
        test_cases = [
            ("Praha", "praɦa"),
            ("chata", "xata"),
            ("děkuji", "ɟɛkujɪ"),
        ]
        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"'{word}': expected '{expected}', got '{result}'"
            )
