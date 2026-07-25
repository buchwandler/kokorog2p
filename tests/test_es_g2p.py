"""Unit tests for Spanish G2P."""

import pytest

from kokorog2p.es import SpanishG2P
from kokorog2p.phonemes import ES_VOCAB


class TestSpanishG2P:
    """Test Spanish G2P phonemization."""

    def test_spacy_options_are_stored(self):
        """Test spaCy option fields are stored on SpanishG2P."""
        g2p = SpanishG2P(use_spacy=True, spacy_model="es_core_news_md")
        assert g2p.use_spacy is True
        assert g2p.spacy_model == "es_core_news_md"

    def test_basic_words(self):
        """Test basic Spanish words."""
        g2p = SpanishG2P()

        assert g2p.phonemize("hola") == "ola"
        assert g2p.phonemize("casa") == "kasa"
        assert g2p.phonemize("perro") == "pero"
        assert g2p.phonemize("gato") == "ɡato"

    def test_vowels(self):
        """Test all 5 Spanish vowels."""
        g2p = SpanishG2P()

        assert g2p.phonemize("papa") == "papa"
        assert g2p.phonemize("bebe") == "bebe"
        assert g2p.phonemize("piso") == "piso"
        assert g2p.phonemize("coco") == "koko"
        assert g2p.phonemize("uva") == "uba"

    def test_palatals(self):
        """Test palatal consonants."""
        g2p = SpanishG2P()

        # ñ -> ɲ
        assert g2p.phonemize("niño") == "niɲo"
        assert g2p.phonemize("año") == "aɲo"

        # ll -> ʎ
        assert g2p.phonemize("llama") == "ʎama"
        assert g2p.phonemize("calle") == "kaʎe"

        # ch -> ʧ
        assert g2p.phonemize("chico") == "ʧiko"
        assert g2p.phonemize("leche") == "leʧe"

    def test_jota(self):
        """Test jota sound (j and g before e/i)."""
        g2p = SpanishG2P(mark_stress=False)  # Disable stress for cleaner test

        # j -> x
        assert g2p.phonemize("jamón") == "xamon"
        assert g2p.phonemize("joven") == "xoben"

        # g + e/i -> x
        assert g2p.phonemize("gente") == "xente"
        assert g2p.phonemize("giro") == "xiɾo"

    def test_theta_european(self):
        """Test theta sound in European Spanish."""
        g2p = SpanishG2P(dialect="es")

        # z -> θ
        assert g2p.phonemize("zapato") == "θapato"
        assert g2p.phonemize("azul") == "aθul"

        # c + e/i -> θ
        assert g2p.phonemize("cielo") == "θielo"
        assert g2p.phonemize("cena") == "θena"

    def test_s_latin_american(self):
        """Test seseo in Latin American Spanish."""
        g2p = SpanishG2P(dialect="la")

        # z -> s
        assert g2p.phonemize("zapato") == "sapato"
        assert g2p.phonemize("azul") == "asul"

        # c + e/i -> s
        assert g2p.phonemize("cielo") == "sielo"
        assert g2p.phonemize("cena") == "sena"

    def test_r_tap_and_trill(self):
        """Test r (tap) vs rr (trill)."""
        g2p = SpanishG2P(mark_stress=False)  # Disable stress for cleaner test

        # Single r between vowels -> ɾ (tap)
        assert g2p.phonemize("pero") == "peɾo"
        assert g2p.phonemize("caro") == "kaɾo"

        # rr -> r (trill)
        assert g2p.phonemize("perro") == "pero"
        assert g2p.phonemize("carro") == "karo"

        # r at word start -> r (trill)
        assert g2p.phonemize("rosa") == "rosa"
        assert g2p.phonemize("río") == "rio"

    def test_qu_gu(self):
        """Test qu and gu combinations."""
        g2p = SpanishG2P()

        # qu + e/i -> k (u is silent)
        assert g2p.phonemize("queso") == "keso"
        assert g2p.phonemize("quien") == "kien"

        # gu + e/i -> ɡ (u is silent)
        assert g2p.phonemize("guerra") == "ɡera"
        assert g2p.phonemize("guiso") == "ɡiso"

    def test_c_soft_hard(self):
        """Test soft and hard c."""
        g2p = SpanishG2P(dialect="es")

        # c + e/i -> θ (soft)
        assert g2p.phonemize("cero") == "θeɾo"
        assert g2p.phonemize("cine") == "θine"

        # c + a/o/u -> k (hard)
        assert g2p.phonemize("casa") == "kasa"
        assert g2p.phonemize("como") == "komo"
        assert g2p.phonemize("cubo") == "kubo"

    def test_g_soft_hard(self):
        """Test soft and hard g."""
        g2p = SpanishG2P()

        # g + e/i -> x (soft, jota)
        assert g2p.phonemize("general") == "xeneɾal"
        assert g2p.phonemize("gitano") == "xitano"

        # g + a/o/u -> ɡ (hard)
        assert g2p.phonemize("gato") == "ɡato"
        assert g2p.phonemize("gota") == "ɡota"
        assert g2p.phonemize("gusto") == "ɡusto"

    def test_silent_h(self):
        """Test that h is silent."""
        g2p = SpanishG2P(dialect="la")  # Use LA dialect to avoid θ

        assert g2p.phonemize("hola") == "ola"
        assert g2p.phonemize("ahora") == "aoɾa"
        assert g2p.phonemize("hacer") == "aseɾ"

    def test_b_v_same(self):
        """Test that b and v are the same sound."""
        g2p = SpanishG2P()

        assert g2p.phonemize("vaca") == "baka"
        assert g2p.phonemize("boca") == "boka"
        assert g2p.phonemize("vino") == "bino"

    def test_stress_marks(self):
        """Test stress marking with accented vowels."""
        g2p = SpanishG2P(mark_stress=True, dialect="la")

        # Stress mark appears AFTER the stressed vowel
        assert g2p.phonemize("café") == "kafeˈ"
        assert g2p.phonemize("música") == "muˈsika"
        # r after vowel is tap ɾ, not trill r
        assert g2p.phonemize("árbol") == "aˈɾbol"

    def test_no_stress_marks(self):
        """Test disabling stress marks."""
        g2p = SpanishG2P(mark_stress=False)

        assert g2p.phonemize("café") == "kafe"
        assert g2p.phonemize("música") == "musika"

    def test_semivowels(self):
        """Test that vowels stay as vowels (TTS handles diphthongs)."""
        g2p = SpanishG2P(dialect="la")

        # Vowels stay as vowels - diphthongs handled by TTS
        # Note: g is IPA ɡ (U+0261) not regular g
        assert g2p.phonemize("agua") == "aɡua"
        assert g2p.phonemize("cuatro") == "kuatɾo"

    def test_y_consonant(self):
        """Test consonantal y."""
        g2p = SpanishG2P()

        assert g2p.phonemize("yo") == "jo"
        assert g2p.phonemize("ayer") == "ajeɾ"

    def test_punctuation(self):
        """Test punctuation handling."""
        g2p = SpanishG2P()

        result = g2p.phonemize("¿Hola, cómo estás?")
        assert "?" in result
        assert "," in result

    def test_sentence(self):
        """Test full sentence."""
        g2p = SpanishG2P(dialect="es")

        result = g2p.phonemize("Buenos días, ¿cómo estás?")
        assert "buenos" in result
        assert "?" in result

    def test_phoneme_validity(self):
        """Test that all generated phonemes are in ES_VOCAB."""
        g2p = SpanishG2P(dialect="es")

        test_words = [
            "hola",
            "adiós",
            "gracias",
            "por favor",
            "bueno",
            "niño",
            "año",
            "mañana",
            "España",
            "señor",
            "queso",
            "quien",
            "guerra",
            "guitarra",
            "zapato",
            "cerveza",
            "cielo",
            "azul",
            "jamón",
            "joven",
            "gente",
            "general",
        ]

        for word in test_words:
            phonemes = g2p.phonemize(word)
            for char in phonemes:
                if char not in (" ", "?", "!", ",", ".", "-", ":", ";", "'", '"'):
                    assert char in ES_VOCAB, (
                        f"Phoneme '{char}' from '{word}'"
                        f" -> '{phonemes}' not in ES_VOCAB"
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
