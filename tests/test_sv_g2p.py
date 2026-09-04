import pytest
from lexphon import DataStore, LexiconNotInstalledError, PronunciationToken

from kokorog2p import get_g2p, phonemize
from kokorog2p.sv import SwedishG2P, normalize_nst_ipa_for_kokoro


def test_public_swedish_g2p_tokenizes_words_and_punctuation() -> None:
    g2p = SwedishG2P()
    tokens = g2p("Hej, sjuk!")
    assert [token.text for token in tokens] == ["Hej", ",", "sjuk", "!"]
    assert tokens[0].phonemes
    assert tokens[1].phonemes == ","
    assert tokens[0].get("raw_ipa")
    assert tokens[0].get("rule_ids")
    assert tokens[0].get("char_start") == 0
    assert tokens[0].get("char_end") == 3
    assert tokens[0].rating == "3"
    assert tokens[1].rating == "4"


def test_lookup_uses_rules_not_a_dictionary() -> None:
    g2p = SwedishG2P()
    assert g2p.lookup("hej") == g2p("hej")[0].phonemes
    assert g2p.capabilities()["runtime_lexicon"] is False


def test_factory_aliases_are_native_and_cached() -> None:
    instances = [
        get_g2p(alias, use_spacy=False, strict=True)
        for alias in ("sv", "sv-se", "swe", "swedish")
    ]
    assert all(isinstance(instance, SwedishG2P) for instance in instances)
    assert len({id(instance) for instance in instances}) == 1
    assert instances[0].use_espeak_fallback is False
    assert instances[0].use_goruut_fallback is False


def test_top_level_phonemize_supports_swedish() -> None:
    result = phonemize(
        "Hej!",
        language="sv",
        use_spacy=False,
        return_ids=False,
    )
    assert result.phonemes
    assert result.tokens[0].text == "Hej"


def test_unknown_word_is_nonfatal_by_default_and_strict_when_requested() -> None:
    assert SwedishG2P()("hello ☃")[0].phonemes
    try:
        SwedishG2P(strict=True).lookup("hello☃")
    except ValueError as exc:
        assert "Swedish" in str(exc)
    else:
        raise AssertionError("strict Swedish rules must reject unsupported letters")


def test_factory_forwards_explicit_swedish_selection() -> None:
    g2p = get_g2p(
        "sv",
        lexicons="nst",
        store=object(),
        use_spacy=False,
        strict=False,
    )
    try:
        assert isinstance(g2p, SwedishG2P)
        assert g2p.lexicons == ("nst",)
    finally:
        g2p.close()


def test_nst_phone_separators_are_removed() -> None:
    assert normalize_nst_ipa_for_kokoro("h e j") == "hej"


def test_missing_explicit_swedish_nst_data_is_actionable(tmp_path) -> None:
    g2p = SwedishG2P(lexicons=("nst",), store=DataStore(tmp_path / "store"))
    try:
        with pytest.raises(
            LexiconNotInstalledError, match="lexphon data install sv-se:nst"
        ):
            g2p.lookup("hej")
    finally:
        g2p.close()


def test_selected_nst_pronunciation_is_converted(monkeypatch) -> None:
    class FakeBackend:
        def __init__(self, language, names, *, store=None) -> None:
            assert language == "sv-se"
            assert tuple(names) == ("nst",)
            self.ids = ("sv-se:nst",)

        def lookup(self, word):
            return PronunciationToken(word, "h e j", "lexicon")

        def close(self) -> None:
            return

    monkeypatch.setattr("kokorog2p.sv.g2p.LexphonBackend", FakeBackend)
    g2p = SwedishG2P(lexicons=("nst",))
    try:
        assert g2p.lookup("hej") == "hɛj"
    finally:
        g2p.close()
