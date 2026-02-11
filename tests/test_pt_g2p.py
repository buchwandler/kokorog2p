"""Tests for Brazilian Portuguese G2P."""

import pytest

from kokorog2p.phonemes import PT_BR_VOCAB
from kokorog2p.pt import PortugueseG2P


class TestPortugueseG2P:
    """Test Brazilian Portuguese G2P conversion."""

    def test_spacy_options_are_stored(self):
        """Test spaCy option fields are stored on PortugueseG2P."""
        g2p = PortugueseG2P(use_spacy=True, spacy_model="pt_core_news_md")
        assert g2p.use_spacy is True
        assert g2p.spacy_model == "pt_core_news_md"

    @pytest.fixture
    def g2p(self):
        """Create a Portuguese G2P instance."""
        return PortugueseG2P(mark_stress=True, affricate_ti_di=True)

    @pytest.fixture
    def g2p_no_stress(self):
        """Create a Portuguese G2P instance without stress markers."""
        return PortugueseG2P(mark_stress=False, affricate_ti_di=True)

    @pytest.fixture
    def g2p_no_affricate(self):
        """Create a Portuguese G2P instance without affrication."""
        return PortugueseG2P(mark_stress=True, affricate_ti_di=False)

    def test_basic_words(self, g2p):
        """Test basic Portuguese words."""
        assert g2p.phonemize("olá") == "olaˈ"
        assert g2p.phonemize("casa") == "kaza"
        assert g2p.phonemize("tia") == "ʧia"  # t+i -> ʧ (affrication)

    def test_vowels(self, g2p):
        """Test all Portuguese vowels."""
        # Oral vowels
        assert "a" in g2p.phonemize("pata")
        assert "e" in g2p.phonemize("peso") or "ɛ" in g2p.phonemize("pé")
        assert "i" in g2p.phonemize("piso")
        assert "o" in g2p.phonemize("bolo") or "ɔ" in g2p.phonemize("pó")
        assert "u" in g2p.phonemize("puro")

    def test_nasal_vowels(self, g2p):
        """Test nasal vowels."""
        assert "ã" in g2p.phonemize("maçã")  # ã (nasal a)
        assert "ã" in g2p.phonemize("não")  # ão -> ãw or ão (contains ã)

    def test_palatals(self, g2p):
        """Test palatal consonants."""
        assert g2p.phonemize("ninho") == "niɲo"  # nh -> ɲ
        assert g2p.phonemize("filho") == "fiʎo"  # lh -> ʎ
        assert g2p.phonemize("chá") == "ʃaˈ"  # ch -> ʃ

    def test_affricates_ti_di(self, g2p):
        """Test affrication of t/d before i (Brazilian Portuguese)."""
        assert g2p.phonemize("tia") == "ʧia"  # t+i -> ʧ
        assert g2p.phonemize("dia") == "ʤia"  # d+i -> ʤ
        assert g2p.phonemize("noite") == "noiʧi"  # te at end -> ʧi

    def test_no_affrication(self, g2p_no_affricate):
        """Test without affrication."""
        assert g2p_no_affricate.phonemize("tia") == "tia"
        assert g2p_no_affricate.phonemize("dia") == "dia"

    def test_sibilants(self, g2p):
        """Test s, z, x sounds."""
        assert g2p.phonemize("casa") == "kaza"  # s between vowels -> z
        assert g2p.phonemize("sim") == "sĩm"  # s at start -> s
        assert g2p.phonemize("xadrez") == "ʃadɾes"  # x -> ʃ, z final -> s

    def test_liquids_r(self, g2p):
        """Test r sounds."""
        assert "r" in g2p.phonemize("rosa")  # word-initial r -> r (trill)
        assert "ɾ" in g2p.phonemize("caro")  # single r -> ɾ (tap)
        assert "r" in g2p.phonemize("carro")  # rr -> r (strong)

    def test_g_soft_hard(self, g2p):
        """Test g before e/i vs a/o/u."""
        assert "ʒ" in g2p.phonemize("gente")  # g+e -> ʒ
        assert "ʒ" in g2p.phonemize("girar")  # g+i -> ʒ
        assert "ɡ" in g2p.phonemize("gato")  # g+a -> ɡ

    def test_c_soft_hard(self, g2p):
        """Test c before e/i vs a/o/u."""
        assert "s" in g2p.phonemize("certo")  # c+e -> s
        assert "s" in g2p.phonemize("cidade")  # c+i -> s
        assert "k" in g2p.phonemize("casa")  # c+a -> k

    def test_qu_gu(self, g2p):
        """Test qu and gu combinations."""
        assert g2p.phonemize("quero") == "keɾo"  # qu+e -> k
        assert g2p.phonemize("guerra") == "ɡera"  # gu+e -> ɡ

    def test_j(self, g2p):
        """Test j sound."""
        assert g2p.phonemize("já") == "ʒaˈ"  # j -> ʒ
        assert g2p.phonemize("jogo") == "ʒoɡo"

    def test_final_l(self, g2p):
        """Test final l -> w."""
        assert g2p.phonemize("Brasil") == "bɾaziw"  # final l -> w
        assert g2p.phonemize("sol") == "sow"

    def test_stress_markers(self, g2p):
        """Test stress marking."""
        assert "ˈ" in g2p.phonemize("café")  # café -> kafeˈ
        assert "ˈ" in g2p.phonemize("olá")  # olá -> olaˈ

    def test_no_stress_markers(self, g2p_no_stress):
        """Test without stress markers."""
        result = g2p_no_stress.phonemize("café")
        assert "ˈ" not in result
        # Vowel quality (open ɛ) should be preserved even without stress marker
        assert result == "kafɛ"

    def test_nasal_consonants(self, g2p):
        """Test nasal consonant combinations."""
        # am, an, em, en, etc. at end or before consonant
        assert "ã" in g2p.phonemize("campo")  # am before p -> ãm
        assert "ẽ" in g2p.phonemize("tempo")  # em before p -> ẽm

    def test_punctuation(self, g2p):
        """Test punctuation handling."""
        result = g2p.phonemize("Olá, tudo bem?")
        assert "," in result
        assert "?" in result

    def test_full_sentences(self, g2p):
        """Test full Portuguese sentences."""
        # Basic greeting
        result = g2p.phonemize("Bom dia")
        assert "bõm" in result or "bom" in result
        assert "ʤia" in result

        # Common phrase
        result = g2p.phonemize("Como você está?")
        # Should have various phonemes

    def test_phoneme_validity(self, g2p):
        """Test that all phonemes are in PT_BR_VOCAB."""
        test_words = [
            "olá",
            "casa",
            "ninho",
            "filho",
            "chá",
            "tia",
            "dia",
            "já",
            "gente",
            "quero",
            "Brasil",
        ]

        for word in test_words:
            phonemes = g2p.phonemize(word)
            for char in phonemes:
                if char not in (" ", "\t", "\n"):
                    assert (
                        char in PT_BR_VOCAB or char in '!?.,;:—…"()❓-'
                    ), f"Invalid phoneme '{char}' in word '{word}' -> '{phonemes}'"
