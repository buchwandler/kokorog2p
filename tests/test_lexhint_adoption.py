from __future__ import annotations

from lexphon import PronunciationToken

from kokorog2p.ko import KoreanG2P
from kokorog2p.pt import PortugueseG2P
from kokorog2p.vi import VietnameseG2P


class FakeBackend:
    def __init__(self, pronunciation: str) -> None:
        self.pronunciation = pronunciation

    def lookup(self, word: str, tag: str | None = None) -> PronunciationToken:
        return PronunciationToken(
            text=word,
            pronunciation=self.pronunciation,
            source="lexicon",
            lexicon_id="test:lexhint",
            matched_key=word,
            source_encoding="ipa",
            variants=(self.pronunciation,),
        )

    def close(self) -> None:
        pass


def test_vietnamese_lexhint_precedes_structural_fallback() -> None:
    g2p = VietnameseG2P(foreign_fallback="none")
    g2p._lexphon = FakeBackend("a")  # type: ignore[assignment]
    analysis = g2p.analyze("not-a-native-syllable")
    assert analysis.classification == "VI_LEXHINT"
    assert analysis.rendered == "a"


def test_korean_lexhint_isolated_word_fast_path() -> None:
    g2p = KoreanG2P(output="ipa")
    g2p._lexphon = FakeBackend("a")  # type: ignore[assignment]
    token = g2p("한글")[0]
    assert token.phonemes == "a"
    assert token.get("lexicon_id") == "ko:lexhint"


def test_portuguese_lexhint_precedes_rules() -> None:
    g2p = PortugueseG2P()
    g2p._lexphon = FakeBackend("a")  # type: ignore[assignment]
    assert g2p.lookup("inexistente") == "a"
