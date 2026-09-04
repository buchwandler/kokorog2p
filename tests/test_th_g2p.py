from __future__ import annotations

import pytest
from lexphon import PronunciationToken

from kokorog2p import clear_cache, get_g2p
from kokorog2p.th.g2p import ThaiG2P, ThaiG2PError


class FakeLexphon:
    def __init__(self, entries: dict[str, str]) -> None:
        self.entries = entries
        self.closed = False

    def lookup_prefixes(self, text: str, *, position: int = 0, tag: str | None = None):
        del tag
        return tuple(
            PronunciationToken(
                text=key,
                pronunciation=self.entries[key],
                source="lexicon",
                lexicon_id="th:lexhint",
                matched_key=key,
                source_encoding="ipa",
                variants=(self.entries[key],),
            )
            for key in sorted(
                (key for key in self.entries if text.startswith(key, position)),
                key=len,
            )
        )

    def close(self) -> None:
        self.closed = True


def _g2p(entries: dict[str, str], **kwargs: object) -> ThaiG2P:
    g2p = ThaiG2P(**kwargs)
    g2p._lexphon = FakeLexphon(entries)  # type: ignore[assignment]
    return g2p


def test_dictionary_segmentation_handles_unspaced_text_and_offsets() -> None:
    g2p = _g2p({"ไทย": "a˩", "ภาษา": "b˩"})
    tokens = g2p("ไทยภาษา!")
    assert [token.text for token in tokens] == ["ไทย", "ภาษา", "!"]
    assert [token.phonemes for token in tokens] == ["a˩", "b˩", "!"]
    assert [(token.get("char_start"), token.get("char_end")) for token in tokens] == [
        (0, 3),
        (3, 7),
        (7, 8),
    ]
    assert tokens[0].get("lexicon_id") == "th:lexhint"
    assert g2p.capabilities()["primary_engine"] == "lexphon"


def test_segmentation_prefers_maximum_coverage_then_longest_leftmost() -> None:
    g2p = _g2p({"ก": "a", "กา": "b", "กาฬ": "c", "ฬ": "d"})
    assert [token.text for token in g2p("กาฬ")] == ["กาฬ"]


def test_unknown_middle_span_is_strict_or_unresolved() -> None:
    strict = _g2p({"ไทย": "a˩", "ภาษา": "b˩"})
    with pytest.raises(ThaiG2PError, match="ก"):
        strict("ไทยกภาษา")

    relaxed = _g2p({"ไทย": "a˩", "ภาษา": "b˩"}, strict=False)
    tokens = relaxed("ไทยกภาษา")
    assert [token.text for token in tokens] == ["ไทย", "ก", "ภาษา"]
    assert tokens[1].phonemes is None
    assert relaxed.warnings


def test_invalid_lexhint_ipa_is_not_silently_dropped() -> None:
    g2p = _g2p({"ไทย": "a¤"}, strict=False)
    token = g2p("ไทย")[0]
    assert token.phonemes is None
    assert "¤" in g2p.warnings[0]


def test_latin_fallback_can_be_disabled_and_runs_are_preserved() -> None:
    g2p = _g2p({}, latin_fallback="none", strict=False)
    token = g2p("hello")[0]
    assert token.phonemes is None
    assert "TH_LATIN_UNRECOVERED" in g2p.warnings[0]
    assert [
        (text, kind) for text, _, _, kind in ThaiG2P._runs("ไทย English, ทดสอบ")
    ] == [
        ("ไทย", "THAI"),
        (" ", "WHITESPACE"),
        ("English", "LATIN"),
        (",", "PUNCTUATION"),
        (" ", "WHITESPACE"),
        ("ทดสอบ", "THAI"),
    ]


def test_factory_defers_lexphon_and_uses_no_implicit_thai_engine() -> None:
    clear_cache()
    g2p = get_g2p(
        "th", use_spacy=False, use_espeak_fallback=False, use_goruut_fallback=False
    )
    assert isinstance(g2p, ThaiG2P)
    assert g2p._lexphon is not None
    assert g2p._lexphon._phonemizer is None
    assert g2p._english_g2p is None
