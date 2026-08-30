"""Tests for the German G2P module."""

import pytest

from kokorog2p.de import GermanG2P, GermanLexicon, GermanNumberConverter
from kokorog2p.de.numbers import expand_number, number_to_german, ordinal_to_german
from kokorog2p.spacy_models import SpacyModelResolution, SpacyModelSize
from kokorog2p.token import GToken


@pytest.fixture(scope="module")
def g2p():
    """Create one shared German G2P instance for mutation-free tests."""
    return GermanG2P()


@pytest.fixture(scope="module")
def g2p_no_lexicon():
    """Create one shared German G2P instance without lexicon."""
    return GermanG2P(use_lexicon=False, use_espeak_fallback=False)


@pytest.fixture(scope="module")
def lexicon():
    """Create one shared German lexicon for lookup tests."""
    return GermanLexicon()



@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("t͡s", "ʦ"),
        ("t͡ʃ", "ʧ"),
        ("d͡ʒ", "ʤ"),
        ("aɪ̯", "aɪ"),
        ("n̩", "n"),
        ("ʏ", "y"),
        ("ʔ", "ʔ"),
        ("ˈhaʊ̯s", "ˈhaʊs"),
        ("haʊs haʊs", "haʊs haʊs"),
    ),
)
def test_crane_ipa_normalization(value, expected):
    from kokorog2p.de.g2p import normalize_to_kokoro

    assert normalize_to_kokoro(value, use_tie_replacement=True) == expected

class TestGermanG2P:
    """Tests for GermanG2P."""

    def test_creation(self, g2p):
        """Test G2P creation."""
        assert g2p.language == "de-de"
        assert g2p.use_spacy is False

    def test_custom_spacy_model_option_is_stored(self):
        """Test custom German spaCy model option is stored."""
        g2p = GermanG2P(
            language="de-de",
            use_spacy=True,
            spacy_model="de_core_news_md",
            use_espeak_fallback=False,
        )
        assert g2p.use_spacy is True
        assert g2p.spacy_model == "de_core_news_md"

    def test_call_returns_tokens(self, g2p):
        """Test calling G2P returns list of tokens."""
        tokens = g2p("Guten Tag")
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
        result = g2p.phonemize("Hallo")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_lookup_method(self, g2p):
        """Test lookup method."""
        ps = g2p.lookup("Haus")
        assert ps is not None
        assert isinstance(ps, str)

    def test_repr(self, g2p):
        """Test string representation."""
        result = repr(g2p)
        assert "GermanG2P" in result
        assert "de-de" in result

    # German-specific phonological tests (rule-based)

    def test_ch_ich_laut(self, g2p_no_lexicon):
        """Test ich-Laut [ç] after front vowels."""
        # ich -> [ɪç]
        result = g2p_no_lexicon.phonemize("ich")
        assert "ç" in result

    def test_ch_ach_laut(self, g2p_no_lexicon):
        """Test ach-Laut [x] after back vowels."""
        # Buch -> [x]
        result = g2p_no_lexicon.phonemize("Buch")
        assert "x" in result

    def test_sch_digraph(self, g2p_no_lexicon):
        """Test sch digraph -> [ʃ]."""
        result = g2p_no_lexicon.phonemize("Schule")
        assert "ʃ" in result

    def test_word_initial_sp(self, g2p_no_lexicon):
        """Test word-initial sp -> [ʃp]."""
        result = g2p_no_lexicon.phonemize("Sport")
        assert "ʃ" in result

    def test_word_initial_st(self, g2p_no_lexicon):
        """Test word-initial st -> [ʃt]."""
        result = g2p_no_lexicon.phonemize("Stadt")
        assert "ʃ" in result

    def test_word_final_ig(self, g2p_no_lexicon):
        """Test word-final -ig -> [ɪç]."""
        result = g2p_no_lexicon.phonemize("richtig")
        assert "ç" in result

    def test_final_devoicing(self, g2p_no_lexicon):
        """Test final obstruent devoicing."""
        # Tag -> final g devoices to k
        result = g2p_no_lexicon.phonemize("Tag")
        assert result.endswith("k")

    def test_diphthong_ei(self, g2p_no_lexicon):
        """Test ei diphthong -> [aɪ̯]."""
        result = g2p_no_lexicon.phonemize("mein")
        assert "aɪ̯" in result or "aɪ" in result

    def test_diphthong_au(self, g2p_no_lexicon):
        """Test au diphthong -> [aʊ] (normalized from aʊ̯)."""
        result = g2p_no_lexicon.phonemize("Haus")
        # After Kokoro normalization: aʊ̯ -> aʊ (combining marker removed)
        assert "aʊ" in result

    def test_diphthong_eu(self, g2p_no_lexicon):
        """Test eu/äu diphthong -> [ɔʏ] (normalized from ɔʏ̯)."""
        result = g2p_no_lexicon.phonemize("neu")
        # After Kokoro normalization: ɔʏ̯ -> ɔy (ʏ also normalized to y)
        assert "ɔy" in result

    def test_umlaut_ae(self, g2p_no_lexicon):
        """Test ä vowel."""
        result = g2p_no_lexicon.phonemize("Männer")
        assert "ɛ" in result

    def test_umlaut_oe(self, g2p_no_lexicon):
        """Test ö vowel."""
        result = g2p_no_lexicon.phonemize("König")
        assert "œ" in result or "ø" in result

    def test_umlaut_ue(self, g2p_no_lexicon):
        """Test ü vowel."""
        result = g2p_no_lexicon.phonemize("Tür")
        assert "ʏ" in result or "y" in result

    def test_eszett(self, g2p_no_lexicon):
        """Test ß -> [s]."""
        result = g2p_no_lexicon.phonemize("groß")
        assert "s" in result

    def test_pf_affricate(self, g2p_no_lexicon):
        """Test pf affricate -> [pf] (no precomposed version in Kokoro)."""
        result = g2p_no_lexicon.phonemize("Pferd")
        # After Kokoro normalization: p͡f -> pf (tie bar removed)
        assert "pf" in result

    def test_z_affricate(self, g2p_no_lexicon):
        """Test z -> [ʦ] (precomposed affricate, normalized from t͡s)."""
        result = g2p_no_lexicon.phonemize("Zeit")
        # After Kokoro normalization: t͡s -> ʦ (U+02A6)
        assert "ʦ" in result

    def test_schwa_in_unstressed_e(self, g2p_no_lexicon):
        """Test schwa in unstressed -e endings."""
        result = g2p_no_lexicon.phonemize("bitte")
        # Final -e should be schwa
        assert "ə" in result

    def test_sentence_with_punctuation(self, g2p):
        """Test sentence with punctuation."""
        tokens = g2p("Wie geht es Ihnen?")
        texts = [t.text for t in tokens]
        assert "Wie" in texts
        assert "?" in texts

    def test_normalized_numbers_reach_tokenization(self):
        g2p = GermanG2P(
            use_lexicon=False,
            use_espeak_fallback=False,
            use_goruut_fallback=False,
        )
        tokens = g2p("Ich habe 42 Euro und 2 kg.")
        assert "42" not in [token.text for token in tokens]
        assert "kg" not in [token.text for token in tokens]
        assert all(
            token.phonemes != "?"
            for token in tokens
            if any(c.isalnum() for c in token.text)
        )


class TestGermanLexicon:
    """Tests for GermanLexicon."""

    def test_creation(self, lexicon):
        """Test lexicon creation."""
        assert len(lexicon) > 0

    def test_lookup_known_word(self, lexicon):
        """Test lookup of known word."""
        result = lexicon.lookup("haus")
        assert result is not None
        assert isinstance(result, str)

    def test_lookup_unknown_word(self, lexicon):
        """Test lookup of unknown word."""
        result = lexicon.lookup("xyznotaword123")
        assert result is None

    def test_is_known(self, lexicon):
        """Test is_known method."""
        assert lexicon.is_known("haus")
        assert not lexicon.is_known("xyznotaword123")



    def test_gold_lookup_remains_case_insensitive(self, lexicon):
        assert lexicon.lookup("haus") == lexicon.lookup("Haus")
        assert lexicon.lookup("haus") == lexicon.lookup("HAUS")

    def test_crane_lookup_uses_source_casing_and_variants(self):
        lexicon = GermanLexicon(lexicons=("crane",), strip_stress=False)
        try:
            assert lexicon.lookup("Haus") == "haʊ̯s"
            assert lexicon.lookup("haus") == "haʊ̯s"
            assert lexicon.is_known("HAUS")
        finally:
            lexicon.close()

    def test_tuple_lookup_uses_first_ordered_pronunciation(self):
        from kokorog2p.lexicons.runtime import LexiconHit

        class Selected:
            def get_hit_candidates(self, words):
                return LexiconHit(
                    ("hˈaʊs", "haʊs"),
                    "fixture",
                    None,
                    "pronunciation",
                    "ipa",
                    "de-de:fixture",
                    {},
                )

        lexicon = GermanLexicon.__new__(GermanLexicon)
        lexicon._selected = Selected()
        lexicon._strip_stress = False
        assert lexicon.lookup("Haus") == "hˈaʊs"

    def test_case_insensitive(self, lexicon):
        """Test case insensitive lookup."""
        result_lower = lexicon.lookup("haus")
        result_upper = lexicon.lookup("HAUS")
        result_mixed = lexicon.lookup("Haus")
        assert result_lower == result_upper == result_mixed

    def test_repr(self, lexicon):
        """Test string representation."""
        result = repr(lexicon)
        assert "GermanLexicon" in result
        assert "entries=" in result


class TestGermanNumberConverter:
    """Tests for GermanNumberConverter."""

    @pytest.fixture
    def converter(self):
        """Create a German number converter instance."""
        return GermanNumberConverter()

    def test_cardinal_single_digit(self, converter):
        """Test single digit cardinals."""
        assert converter.convert_cardinal("1") == "eins"
        assert converter.convert_cardinal("5") == "fünf"
        assert converter.convert_cardinal("0") == "null"

    def test_cardinal_teens(self, converter):
        """Test teen numbers."""
        assert converter.convert_cardinal("11") == "elf"
        assert converter.convert_cardinal("12") == "zwölf"
        assert converter.convert_cardinal("17") == "siebzehn"

    def test_cardinal_tens(self, converter):
        """Test tens."""
        assert converter.convert_cardinal("20") == "zwanzig"
        assert converter.convert_cardinal("30") == "dreißig"
        assert converter.convert_cardinal("21") == "einundzwanzig"
        assert converter.convert_cardinal("42") == "zweiundvierzig"

    def test_cardinal_hundreds(self, converter):
        """Test hundreds."""
        # num2words returns "einhundert", our fallback returns "hundert"
        result_100 = converter.convert_cardinal("100")
        assert result_100 in ("hundert", "einhundert")
        result_200 = converter.convert_cardinal("200")
        assert result_200 == "zweihundert"
        result_123 = converter.convert_cardinal("123")
        assert "hundert" in result_123 and "dreiundzwanzig" in result_123

    def test_cardinal_thousands(self, converter):
        """Test thousands."""
        assert converter.convert_cardinal("1000") == "eintausend"
        assert converter.convert_cardinal("2000") == "zweitausend"

    def test_ordinal(self, converter):
        """Test ordinal conversion."""
        assert converter.convert_ordinal("1") == "erste"
        assert converter.convert_ordinal("3") == "dritte"
        assert converter.convert_ordinal("7") == "siebte"
        assert converter.convert_ordinal("20") == "zwanzigste"

    def test_year(self, converter):
        """Test year conversion."""
        result = converter.convert_year("1984")
        assert "neunzehn" in result
        assert "hundert" in result

        result2 = converter.convert_year("2024")
        assert "zweitausend" in result2

    def test_decimal(self, converter):
        """Test decimal conversion."""
        result = converter.convert_decimal("3,14")
        assert "drei" in result
        assert "Komma" in result

    def test_currency(self, converter):
        """Test currency conversion."""
        result = converter.convert_currency("12,50", "€")
        assert "zwölf" in result
        assert "Euro" in result
        assert "fünfzig" in result


class TestGermanNumberFunctions:
    """Tests for standalone number conversion functions."""

    def test_number_to_german(self):
        """Test number_to_german function."""
        assert number_to_german(0) == "null"
        assert number_to_german(1) == "eins"
        assert number_to_german(21) == "einundzwanzig"
        assert number_to_german(-5) == "minus fünf"

    def test_ordinal_to_german(self):
        """Test ordinal_to_german function."""
        assert ordinal_to_german(1) == "erste"
        assert ordinal_to_german(3) == "dritte"
        assert ordinal_to_german(8) == "achte"

    def test_expand_number(self):
        """Test expand_number function."""
        result = expand_number("Ich habe 42 Bücher.")
        assert "zweiundvierzig" in result

        # Test simple number expansion (currency pattern is complex)
        result2 = expand_number("Preis: 12,50")
        assert "zwölf" in result2
        assert "Komma" in result2


class TestGermanGetG2P:
    """Tests for get_g2p with German."""

    def test_get_g2p_german(self):
        """Test get_g2p returns GermanG2P for German."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p = get_g2p("de")
        assert isinstance(g2p, GermanG2P)

        clear_cache()
        g2p = get_g2p("de-de")
        assert isinstance(g2p, GermanG2P)

        clear_cache()
        g2p = get_g2p("german")
        assert isinstance(g2p, GermanG2P)

        clear_cache()
        g2p = get_g2p("deu")
        assert isinstance(g2p, GermanG2P)

    def test_get_g2p_german_variants(self):
        """Test get_g2p with German regional variants."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p_at = get_g2p("de-at")  # Austrian German
        assert isinstance(g2p_at, GermanG2P)

        clear_cache()
        g2p_ch = get_g2p("de-ch")  # Swiss German
        assert isinstance(g2p_ch, GermanG2P)

    def test_get_g2p_german_forwards_use_spacy(self, monkeypatch):
        """Test get_g2p forwards use_spacy for German."""
        from kokorog2p import clear_cache, get_g2p

        monkeypatch.setattr(
            "kokorog2p.resolve_spacy_model",
            lambda *_args, **_kwargs: SpacyModelResolution(
                language="de",
                package="de_core_news_sm",
                size=SpacyModelSize.SM,
                automatic=True,
                candidates=("de_core_news_sm",),
                checked=("de_core_news_sm",),
                errors=(),
                spacy_available=True,
            ),
        )
        clear_cache()
        g2p = get_g2p("de", use_spacy=True)
        assert isinstance(g2p, GermanG2P)
        assert g2p.use_spacy is True
        assert g2p.spacy_model == "de_core_news_sm"

    def test_get_g2p_preserves_german_default_when_model_is_unset(self):
        """German keeps its existing spaCy-disabled default."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()
        g2p = get_g2p("de", spacy_model="de_core_news_md")
        assert isinstance(g2p, GermanG2P)
        assert g2p.use_spacy is False
        assert g2p.spacy_model is None
