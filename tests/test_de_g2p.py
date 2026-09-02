"""Tests for the German G2P module."""

from importlib.util import find_spec

import pytest

from kokorog2p import phonemize
from kokorog2p.de import GermanG2P, GermanLexicon
from kokorog2p.pipeline_api import phonemize_to_result
from kokorog2p.spacy_models import SpacyModelResolution, SpacyModelSize
from kokorog2p.token import GToken
from kokorog2p.types import OverrideSpan
from kokorog2p.vocab import validate_for_kokoro


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
        ("aɪ̯", "I"),
        ("n̩", "n"),
        ("ʏ", "y"),
        ("ʔ", "ʔ"),
        ("ˈhaʊ̯s", "ˈhWs"),
        ("haʊs haʊs", "hWs hWs"),
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

    def test_tagged_lookup_normalizes_selected_source_pronunciation(self):
        class TaggedLexicon:
            def __init__(self):
                self.tag = None
                self.word = None

            def lookup(self, word, tag=None):
                self.word = word
                self.tag = tag
                return "aɪ̯"

            def close(self):
                pass

        g2p = GermanG2P(
            use_lexicon=False,
            use_espeak_fallback=False,
            use_goruut_fallback=False,
        )
        lexicon = TaggedLexicon()
        g2p._lexicon = lexicon
        try:
            assert g2p.lookup("Test", "NN") == "I"
            assert lexicon.word == "Test"
            assert lexicon.tag == "NN"
        finally:
            g2p.close()

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
        assert "I" in result

    def test_diphthong_au(self, g2p_no_lexicon):
        """Test au diphthong -> [aʊ] (normalized from aʊ̯)."""
        result = g2p_no_lexicon.phonemize("Haus")
        # German Crane/Kokoro profile uses the explicit W diphthong token.
        assert "W" in result

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

    def test_prepared_numbers_reach_tokenization(self):
        g2p = GermanG2P(
            use_lexicon=False,
            use_espeak_fallback=False,
            use_goruut_fallback=False,
        )
        tokens = g2p("Ich habe 42 Euro und 2 kg.")
        texts = [token.text for token in tokens]
        assert "42" in texts
        assert "kg" in texts


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

    def test_direct_selection_rejects_duplicate_names(self):
        with pytest.raises(ValueError, match="duplicate"):
            GermanLexicon(lexicons=("gold", "gold"))

    def test_direct_selection_rejects_unknown_names_with_valid_names(self):
        with pytest.raises(ValueError, match="valid names: gold, crane"):
            GermanLexicon(lexicons=("missing",))

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

    def test_crane_sentence_initial_die_uses_default_article_pronunciation(self):
        g2p = GermanG2P(
            lexicons=("crane",),
            use_spacy=False,
            use_espeak_fallback=False,
            use_goruut_fallback=False,
            strip_stress=False,
        )
        try:
            tokens = g2p("Die Leute")
            assert tokens[0].text == "Die"
            assert tokens[0].phonemes == "diː"
        finally:
            g2p.close()

    def test_crane_die_uses_lowercase_runtime_selectors(self):
        lexicon = GermanLexicon(lexicons=("crane",), strip_stress=False)
        try:
            assert lexicon.lookup("die") == "diː"
            assert lexicon.lookup("Die") == "diː"
            assert lexicon.lookup("DIE") == "diː"
            assert lexicon.lookup("die", tag="DET") == "diː"
            assert lexicon.lookup("die", tag="ART") == "diː"
            assert lexicon.lookup("die", tag="PRON") == "diː"
        finally:
            lexicon.close()

    @pytest.mark.spacy
    def test_crane_sentence_initial_die_with_spacy_pos(self):
        if find_spec("de_core_news_sm") is None:
            pytest.skip("spaCy model de_core_news_sm is not installed")
        g2p = GermanG2P(
            lexicons=("crane",),
            use_spacy=True,
            spacy_model="de_core_news_sm",
            use_espeak_fallback=False,
            use_goruut_fallback=False,
            strip_stress=False,
        )
        try:
            tokens = g2p("Die Leute")
            assert tokens[0].tag == "ART"
            assert tokens[0].phonemes == "diː"
        finally:
            g2p.close()

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


@pytest.mark.parametrize("source", ["gold", "crane", "espeak", "olaph"])
def test_german_stress_is_relative_across_sources(source):
    g2p = GermanG2P(
        lexicons=(source,),
        strip_stress=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    try:
        base = g2p("zwei")[0].phonemes
        raised = phonemize_to_result(
            "zwei",
            lang="de",
            g2p=g2p,
            overrides=[OverrideSpan(0, 4, {"stress": "+2"})],
            return_ids=False,
        ).phonemes
    finally:
        g2p.close()

    assert base is not None
    if "ˈ" in base:
        assert raised == base
    else:
        assert raised is not None and "ˈ" in raised


@pytest.mark.parametrize("source", ["gold", "crane", "espeak", "olaph"])
def test_german_without_stress_override_is_unchanged(source):
    g2p = GermanG2P(
        lexicons=(source,),
        strip_stress=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    try:
        direct = " ".join(
            token.phonemes or "" for token in g2p("zwei") if token.phonemes
        )
        result = phonemize_to_result(
            "zwei", lang="de", g2p=g2p, return_ids=False
        ).phonemes
    finally:
        g2p.close()

    assert result == direct


def test_german_strip_stress_then_explicit_stress():
    g2p = GermanG2P(
        lexicons=("gold",),
        strip_stress=True,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    try:
        result = phonemize_to_result(
            "zwei",
            lang="de",
            g2p=g2p,
            overrides=[OverrideSpan(0, 4, {"stress": "+2"})],
            return_ids=False,
        ).phonemes
    finally:
        g2p.close()

    assert result == "ʦvˈI"


@pytest.mark.parametrize("source", ["gold", "crane", "espeak", "olaph"])
def test_named_german_lexicons_are_vocab_safe_with_token_ids(source):
    text = "Haus fünf Zeit"
    g2p = GermanG2P(
        lexicons=(source,),
        strip_stress=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    try:
        result = phonemize(
            text,
            language="de",
            g2p=g2p,
            return_phonemes=True,
            return_ids=True,
        )
    finally:
        g2p.close()

    assert result.token_ids
    assert result.phonemes
    assert validate_for_kokoro(result.phonemes) == (True, [])
    assert not any(
        warning.startswith("[VOCAB] invalid chars") for warning in result.warnings
    )
    assert all(char not in result.phonemes for char in "̩̯͡ʏ")


@pytest.mark.parametrize("source", ["gold", "crane", "espeak", "olaph"])
def test_named_german_lexicons_match_direct_and_public_pipeline(source):
    text = "Haus fünf Zeit"
    g2p = GermanG2P(
        lexicons=(source,),
        strip_stress=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    try:
        direct = " ".join(token.phonemes or "" for token in g2p(text) if token.phonemes)
        result = phonemize(
            text,
            language="de",
            g2p=g2p,
            return_phonemes=True,
            return_ids=True,
        )
    finally:
        g2p.close()

    assert result.phonemes == direct
