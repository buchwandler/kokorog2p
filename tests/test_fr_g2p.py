"""Tests for the French G2P module."""

from kokorog2p.fr import FrenchG2P
from kokorog2p.token import GToken


class TestFrenchG2P:
    """Tests for FrenchG2P."""

    def test_creation_defaults(self):
        """Test FrenchG2P default configuration."""
        g2p = FrenchG2P(use_espeak_fallback=False)
        assert g2p.language == "fr-fr"
        assert g2p.use_spacy is True
        assert g2p.spacy_model == "fr_core_news_sm"

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

    def test_get_g2p_french_forwards_spacy_model(self):
        """Test get_g2p forwards custom French spaCy model name."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p = get_g2p("fr", spacy_model="fr_core_news_md")

        assert isinstance(g2p, FrenchG2P)
        assert g2p.spacy_model == "fr_core_news_md"
