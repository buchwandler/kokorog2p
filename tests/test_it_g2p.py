"""Tests for Italian G2P converter."""

import pytest

from kokorog2p.it import ItalianG2P
from kokorog2p.phonemes import IT_VOCAB


class TestItalianG2P:
    """Test suite for Italian G2P."""

    def test_spacy_options_are_stored(self):
        """Test spaCy option fields are stored on ItalianG2P."""
        g2p = ItalianG2P(use_spacy=True, spacy_model="it_core_news_md")
        assert g2p.use_spacy is True
        assert g2p.spacy_model == "it_core_news_md"

    @pytest.fixture
    def g2p(self):
        """Create an Italian G2P instance."""
        return ItalianG2P()

    def test_basic_words(self, g2p):
        """Test basic Italian words."""
        test_cases = [
            ("ciao", "ʧiao"),
            ("grazie", "ɡraʦie"),
            ("pizza", "piʦːa"),
            ("pasta", "pasta"),
            ("gelato", "ʤelato"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_palatals(self, g2p):
        """Test palatal consonants (gn, gli)."""
        test_cases = [
            ("gnocchi", "ɲokːi"),
            ("famiglia", "famiʎa"),
            ("bagno", "baɲo"),
            ("figlio", "fiʎo"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_affricates(self, g2p):
        """Test affricates (c/ci, g/gi, z)."""
        test_cases = [
            ("ciao", "ʧiao"),
            ("cena", "ʧena"),
            ("giorno", "ʤiorno"),
            ("gelato", "ʤelato"),
            ("pizza", "piʦːa"),
            ("zio", "ʦio"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_velar_consonants(self, g2p):
        """Test velar consonants (c/ch, g/gh)."""
        test_cases = [
            ("casa", "kasa"),
            ("che", "ke"),
            ("chi", "ki"),
            ("gatto", "ɡatːo"),
            ("ghetto", "ɡetːo"),
            ("ghiro", "ɡiro"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_sc_combinations(self, g2p):
        """Test 'sc' combinations."""
        test_cases = [
            ("pesce", "peʃe"),
            ("scienza", "ʃienʦa"),
            ("scuola", "skuola"),
            ("scarpa", "skarpa"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_gemination(self, g2p):
        """Test double consonants (gemination)."""
        test_cases = [
            ("pizza", "piʦːa"),
            ("cappuccino", "kapːuʧːino"),
            ("spaghetti", "spaɡetːi"),
            ("mamma", "mamːa"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_stress_marks(self, g2p):
        """Test stress marking with accented vowels."""
        test_cases = [
            ("città", "ʧitːaˈ"),
            ("perché", "perkeˈ"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_silent_h(self, g2p):
        """Test silent 'h'."""
        test_cases = [
            ("hanno", "anːo"),
            ("hotel", "otel"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_qu_combination(self, g2p):
        """Test 'qu' combinations."""
        test_cases = [
            ("quando", "kwando"),
            ("questo", "kwesto"),
            ("acqua", "akːwa"),
        ]

        for word, expected in test_cases:
            result = g2p.phonemize(word)
            assert result == expected, (
                f"Expected '{expected}' but got '{result}' for '{word}'"
            )

    def test_punctuation(self, g2p):
        """Test punctuation handling."""
        text = "Ciao, come stai?"
        tokens = g2p(text)

        # Check that punctuation is preserved
        assert any(t.phonemes == "," for t in tokens)
        assert any(t.phonemes == "?" for t in tokens)

    def test_sentence(self, g2p):
        """Test full sentence conversion."""
        sentence = "Buongiorno, mi chiamo Mario."
        tokens = g2p(sentence)

        # Should have multiple tokens
        assert len(tokens) > 0

        # All word tokens should have phonemes
        for token in tokens:
            if token.is_word:
                assert token.phonemes is not None
                assert token.phonemes != "?"

    def test_phoneme_validity(self, g2p):
        """Test that all generated phonemes are in IT_VOCAB."""
        test_words = [
            "ciao",
            "grazie",
            "buongiorno",
            "arrivederci",
            "gnocchi",
            "famiglia",
            "pesce",
            "pizza",
            "spaghetti",
            "cappuccino",
            "gelato",
            "città",
        ]

        for word in test_words:
            phonemes = g2p.phonemize(word)
            for phoneme in phonemes:
                if phoneme.strip():  # Ignore whitespace
                    assert phoneme in IT_VOCAB, (
                        f"Phoneme '{phoneme}' from '{word}' not in IT_VOCAB"
                    )

    def test_empty_input(self, g2p):
        """Test empty input."""
        assert g2p("") == []
        assert g2p("   ") == []

    def test_lookup(self, g2p):
        """Test lookup method."""
        result = g2p.lookup("ciao")
        assert result == "ʧiao"

    def test_repr(self, g2p):
        """Test string representation."""
        assert "Italian" in repr(g2p)
        assert "it" in repr(g2p).lower()
