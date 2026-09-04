from __future__ import annotations

import pytest
from lexphon import PronunciationToken

from kokorog2p.ru import RussianG2P


class FakeLexphon:
    def __init__(self, pronunciation: str = "ˈslovo") -> None:
        self.pronunciation = pronunciation
        self.closed = False

    def lookup(self, word: str, tag: str | None = None) -> PronunciationToken:
        return PronunciationToken(
            text=word,
            pronunciation=self.pronunciation,
            source="lexicon",
            lexicon_id="ru:lexhint",
            matched_key=word,
            source_encoding="ipa",
            variants=(self.pronunciation,),
        )

    def close(self) -> None:
        self.closed = True


def _g2p(**kwargs: object) -> RussianG2P:
    g2p = RussianG2P(**kwargs)
    g2p._lexphon = FakeLexphon()  # type: ignore[assignment]
    return g2p


def test_russian_lexhint_provenance_and_offsets() -> None:
    g2p = _g2p()
    tokens = g2p("слово!")
    assert [token.text for token in tokens] == ["слово", "!"]
    assert tokens[0].phonemes == "ˈslovo"
    assert tokens[0].get("source_kind") == "RUSSIAN_WORD"
    assert tokens[0].get("source") == "lexicon"
    assert tokens[0].get("lexicon_id") == "ru:lexhint"
    assert (tokens[0].get("char_start"), tokens[0].get("char_end")) == (0, 5)


def test_preserve_stress_controls_dictionary_stress() -> None:
    assert _g2p(preserve_stress=True)._word_analysis("слово").phonemes == "ˈslovo"
    assert _g2p(preserve_stress=False)._word_analysis("слово").phonemes == "slovo"


def test_unknown_words_are_strict_or_unresolved() -> None:
    class UnknownLexphon(FakeLexphon):
        def lookup(self, word: str, tag: str | None = None):
            return PronunciationToken(word, None, "unknown")

    strict = RussianG2P()
    strict._lexphon = UnknownLexphon()  # type: ignore[assignment]
    with pytest.raises(ValueError, match="ru:lexhint"):
        strict("неслово")

    relaxed = RussianG2P(strict=False)
    relaxed._lexphon = UnknownLexphon()  # type: ignore[assignment]
    assert relaxed("неслово")[0].phonemes is None
    assert relaxed.warnings


def test_latin_policy_and_no_hidden_espeak() -> None:
    preserved = _g2p(latin_policy="preserve")("hello")
    assert preserved[0].get("source_kind") == "LATIN_PRESERVED"
    dropped = _g2p(latin_policy="drop")("hello")
    assert dropped[0].get("source_kind") == "LATIN_DROPPED"
    assert dropped[0].get("drop") is True
