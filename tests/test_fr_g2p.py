"""Tests for the French G2P module."""

from unittest.mock import patch

from kokorog2p.fr import FrenchG2P
from kokorog2p.fr.fallback import FrenchFallback
from kokorog2p.fr.lexicon import FrenchLexicon
from kokorog2p.token import GToken


class TestFrenchG2P:
    """Tests for FrenchG2P."""

    def test_creation_defaults(self):
        """Test FrenchG2P default configuration."""
        g2p = FrenchG2P(use_espeak_fallback=False)
        assert g2p.language == "fr-fr"
        assert g2p.use_spacy is True
        assert g2p.spacy_model == "fr_core_news_sm"

    def test_french_fallback_inherits_use_cli(self):
        g2p = FrenchG2P(
            use_spacy=False,
            use_cli=True,
            load_gold=False,
        )

        assert g2p.use_cli is True
        assert g2p.fallback is not None
        assert g2p.fallback.use_cli is True
        assert g2p.fallback.backend.use_cli is True

    def test_call_returns_tokens_without_spacy(self):
        """Test token output without requiring spaCy model."""
        g2p = FrenchG2P(use_spacy=False, use_espeak_fallback=False)
        tokens = g2p("Bonjour le monde!")

        assert isinstance(tokens, list)
        assert all(isinstance(t, GToken) for t in tokens)
        assert any(t.text == "Bonjour" for t in tokens)
        assert any(t.text == "!" for t in tokens)


class TestFrenchGetG2P:
    """Tests for get_g2p with French options."""

    def test_get_g2p_french_forwards_use_spacy(self):
        """Test get_g2p forwards use_spacy for French."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p = get_g2p("fr", use_spacy=False)

        assert isinstance(g2p, FrenchG2P)
        assert g2p.use_spacy is False

    def test_get_g2p_french_forwards_use_cli(self):
        """Test get_g2p forwards CLI selection to the French fallback."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p = get_g2p("fr", use_cli=True, use_spacy=False, load_gold=False)

        assert isinstance(g2p, FrenchG2P)
        assert g2p.use_cli is True
        assert g2p.fallback is not None
        assert g2p.fallback.use_cli is True

    def test_get_g2p_french_forwards_spacy_model(self):
        """Test get_g2p forwards custom French spaCy model name."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p = get_g2p("fr", spacy_model="fr_core_news_md")

        assert isinstance(g2p, FrenchG2P)
        assert g2p.spacy_model == "fr_core_news_md"


class TestFrenchFallback:
    def test_uses_locale_specific_standard_espeak_language(self):
        fallback = FrenchFallback()

        assert fallback.backend.language == "fr-fr"

    def test_rejects_empty_or_placeholder_phonemes(self):
        fallback = FrenchFallback()

        with patch.object(fallback, "_backend_word_phonemes", return_value=""):
            assert fallback("xyzzy") == (None, 0)

        with patch.object(fallback, "_backend_word_phonemes", return_value="?"):
            assert fallback("xyzzy") == (None, 0)

        with patch.object(fallback, "_backend_word_phonemes", return_value="  "):
            assert fallback("xyzzy") == (None, 0)


class TestFrenchGoldLexicon:
    """Regression tests for corrected French gold IPA entries."""

    def test_nasal_vowel_and_verb_ending_entries(self):
        lexicon = FrenchLexicon(load_silver=False, load_gold=True)

        expected = {
            "demander": "dəmɑ̃de",
            "restaurant": "ʁɛstɔʁɑ̃",
            "restaurants": "ʁɛstɔʁɑ̃",
            "excellent": "ɛksɛlɑ̃",
            "excellents": "ɛksɛlɑ̃",
            "excellente": "ɛksɛlɑ̃t",
            "excellentes": "ɛksɛlɑ̃t",
        }

        for word, phonemes in expected.items():
            ps, rating = lexicon(word)
            assert ps == phonemes, f"{word}: expected {phonemes!r}, got {ps!r}"
            assert rating == 4
