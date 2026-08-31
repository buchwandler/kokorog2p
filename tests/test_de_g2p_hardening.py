"""Regression tests for strict German Crane consumer decoding."""

from kokorog2p.de import GermanG2P
from kokorog2p.de.g2p import normalize_internal


def test_unsupported_material_is_rejected_without_silent_deletion() -> None:
    result = normalize_internal("a§b", vocabulary={"a", "b"})
    assert not result.valid
    assert result.value == "a§b"
    assert "§" in result.unsupported


def test_unsupported_only_pronunciation_is_not_a_successful_result() -> None:
    result = normalize_internal("§", vocabulary={"a"})
    assert not result.valid
    assert result.value == "§"


def test_explicitly_ignored_mark_is_classified_and_stable() -> None:
    result = normalize_internal("aɪ̯", use_tie_replacement=True)
    assert result.valid
    assert result.value == "I"
    assert result.ignored == ("̯",)
    assert result.unsupported == ()


def test_nfc_equivalent_ipa_is_normalized_identically() -> None:
    composed = normalize_internal("ạ")
    decomposed = normalize_internal("a\u0323")
    assert composed == decomposed
    assert composed.value == "a"


def test_restricted_target_vocabulary_is_used_instead_of_global_default() -> None:
    result = normalize_internal("aɪ", vocabulary={"a", "ɪ"})
    assert not result.valid
    assert result.value == "I"
    assert result.unsupported == ()


def test_invalid_dictionary_result_allows_fallback() -> None:
    class BadLexicon:
        def lookup(self, word, tag=None):
            return "§"

    class Fallback:
        def __call__(self, word):
            return ("fallback",)

    g2p = GermanG2P(
        use_lexicon=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    g2p._lexicon = BadLexicon()
    g2p._fallback = Fallback()
    token = next(token for token in g2p("Haus") if token.is_word)
    assert token.phonemes == "fallback"
    assert token.get("rating") == 3


def test_real_olaph_invalid_pronunciation_falls_back() -> None:
    g2p = GermanG2P(
        lexicons=("olaph",),
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        use_spacy=False,
        expand_abbreviations=False,
        enable_context_detection=False,
        strip_stress=False,
    )
    try:
        assert "/" in g2p._lexicon.lookup("Beer")
        token = next(token for token in g2p("Beer") if token.is_word)
        assert token.phonemes == "beːʁ"
        assert token.get("rating") == 2
        assert "/" not in token.phonemes
    finally:
        g2p.close()


def test_static_espeak_lexicon_works_without_espeak_fallback() -> None:
    g2p = GermanG2P(
        lexicons=("espeak",),
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        use_spacy=False,
        expand_abbreviations=False,
        enable_context_detection=False,
        strip_stress=False,
    )
    try:
        token = next(token for token in g2p("Haus") if token.is_word)
        assert token.phonemes == "hˈWs"
        assert token.get("rating") == 5
    finally:
        g2p.close()


def test_consumer_parity_validates_first_variant_and_target_vocab() -> None:
    from kokorog2p.lexicons.runtime import _consumer_decode_parity

    result = _consumer_decode_parity(
        {"Haus": ("h aʊ s", "h ə s")},
        language="de-de",
        phoneme_encoding="ipa",
    )
    assert result["decoded_entries"] == 1
    assert result["invalid_first_pronunciations"] == 0
    assert result["ok"] is True


def test_consumer_parity_reports_invalid_fixture() -> None:
    from kokorog2p.lexicons.runtime import _consumer_decode_parity

    result = _consumer_decode_parity(
        {"fixture": "a§b"},
        language="de-de",
        phoneme_encoding="ipa",
    )
    assert result["invalid_first_pronunciations"] == 1
    assert result["unsupported_source_sequences"] == {"§": 1}
    assert result["ok"] is False
