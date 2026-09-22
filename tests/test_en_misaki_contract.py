import json
from pathlib import Path

import pytest

from kokorog2p.en import EnglishG2P
from kokorog2p.en import lexicon as en_lexicon
from kokorog2p.lexicons.runtime import LexiconHit


class FakeSelected:
    def __init__(self, values: dict[str, object]) -> None:
        self.values = values

    def get_hit(self, word: str) -> LexiconHit | None:
        if word not in self.values:
            return None
        return LexiconHit(
            value=self.values[word],
            name="lexhint",
            rating=None,
            kind="pronunciation",
            phoneme_encoding="ipa",
            lexicon_id="en-us:lexhint",
            metadata={"id": "en-us:lexhint"},
        )

    def __contains__(self, word: object) -> bool:
        return word in self.values

    def close(self) -> None:
        pass


def _g2p(monkeypatch: pytest.MonkeyPatch) -> EnglishG2P:
    selected = FakeSelected(
        {
            "apple": "ˈæpəl",
            "eat": "iːt",
            "hello": "həˈloʊ",
            "camel": "ˈkæməl",
            "aa": "ˈɑ.ɑ",
            "case": "ˈkeɪs",
            "A": {"CHARACTER": "eɪ", "DEFAULT": "eɪ"},
            "B": {"CHARACTER": "bi", "DEFAULT": "bi"},
            "to": "tu",
        }
    )
    monkeypatch.setattr(en_lexicon, "open_selected", lambda *args, **kwargs: selected)
    return EnglishG2P(
        language="en-us",
        lexicons=("lexhint",),
        use_spacy=False,
        use_espeak_fallback=False,
    )


def test_lexhint_uses_common_codec_and_compound_realizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    g2p = _g2p(monkeypatch)
    try:
        assert g2p.lookup("hello") == "həˈlO"
        assert g2p.lookup("aa") == "ˈɑɑ"
        assert g2p.lookup("CamelCase") == "ˈkæməlˌkAs"
        spelling = g2p.lexicon.get_NNP("AB")[0]
        assert spelling is not None
        assert "eɪ" not in spelling
    finally:
        g2p.close()


def test_context_uses_decoded_phonemes_and_resets_at_punctuation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    g2p = _g2p(monkeypatch)
    try:
        assert [token.phonemes for token in g2p("the apple") if token.text.strip()] == [
            "ði",
            "ˈæpəl",
        ]
        actual = [token.phonemes for token in g2p("the, apple") if token.text.strip()]
        assert actual == [
            "ðə",
            ",",
            "ˈæpəl",
        ]
        assert [token.phonemes for token in g2p("to eat") if token.text.strip()] == [
            "tʊ",
            "it",
        ]
    finally:
        g2p.close()


def test_contract_corpus_contains_stage_schema() -> None:
    path = Path("benchmarks/reference/data/en_us_misaki_contract_v1.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["metadata"]["stage_schema"] == [
        "source_selection",
        "source_decoding",
        "derived_pronunciation",
        "compound_stress",
        "final_pronunciation",
    ]
    assert len(payload["cases"]) >= 40
