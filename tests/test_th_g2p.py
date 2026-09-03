"""Tests for the native Thai G2P frontend."""

from dataclasses import dataclass

import pytest

from kokorog2p import clear_cache, get_g2p
from kokorog2p.th.engine import EngineResult, ThaiG2PError
from kokorog2p.th.g2p import ThaiG2P


@dataclass
class FakeEngine:
    unrecovered: list[str] | None = None

    def pronounce_thai_chunk(self, source: str) -> EngineResult:
        return EngineResult(
            source=source,
            raw_ipa="a2",
            unrecovered=list(self.unrecovered or []),
        )


class FakeEnglish:
    def phonemize(self, text: str) -> str:
        return "hˈɛlO wˈɜɹld" if text == "text to speech" else "wˈɜɹd"


def test_pure_thai_does_not_create_english_frontend() -> None:
    g2p = ThaiG2P(engine=FakeEngine(), latin_fallback="english")
    tokens = g2p("สวัสดี")
    assert tokens[0].phonemes == "a˩"
    assert tokens[0].get("classification") == "THAI"
    assert g2p._english_g2p is None


def test_mixed_runs_preserve_phrase_and_offsets() -> None:
    g2p = ThaiG2P(engine=FakeEngine())
    g2p._english_g2p = FakeEnglish()  # type: ignore[assignment]

    tokens = g2p("ไทย text to speech!")

    assert [token.text for token in tokens] == ["ไทย", "text to speech", "!"]
    assert tokens[0].get("char_start") == 0
    assert tokens[0].get("char_end") == 3
    assert tokens[1].get("char_start") == 4
    assert tokens[1].get("char_end") == 18
    assert tokens[1].phonemes == "hˈɛlO wˈɜɹld"
    assert tokens[0].whitespace == " "
    assert tokens[1].whitespace == ""
    assert tokens[2].is_punctuation


def test_latin_fallback_can_be_disabled() -> None:
    g2p = ThaiG2P(engine=FakeEngine(), latin_fallback="none", strict=False)
    tokens = g2p("hello")
    assert tokens[0].phonemes is None
    assert "TH_LATIN_UNRECOVERED" in g2p.warnings[0]


def test_strict_mode_reports_unrecovered_lexical_units() -> None:
    g2p = ThaiG2P(engine=FakeEngine(unrecovered=["กลาง"]))
    with pytest.raises(ThaiG2PError, match="recover"):
        g2p("กลาง")


def test_target_model_and_capabilities() -> None:
    g2p = ThaiG2P(engine=FakeEngine())
    assert g2p.version == "1.0"
    assert g2p.get_target_model() == "wayu-kokoro-thai-v1"
    assert g2p.capabilities()["primary_engine"] == "tltk"


def test_thai_script_segmentation_is_deterministic() -> None:
    runs = ThaiG2P._runs("ไทย English, ทดสอบ")
    assert [(text, kind) for text, _, _, kind in runs] == [
        ("ไทย", "THAI"),
        (" ", "WHITESPACE"),
        ("English", "LATIN"),
        (",", "PUNCTUATION"),
        (" ", "WHITESPACE"),
        ("ทดสอบ", "THAI"),
    ]


def test_factory_defers_default_thai_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[bool] = []

    class LazyEngine:
        def __init__(self, *, strict: bool) -> None:
            calls.append(strict)

        def pronounce_thai_chunk(self, source: str) -> EngineResult:
            return EngineResult(source=source, raw_ipa="a2")

    monkeypatch.setattr("kokorog2p.th.g2p.ThaiEngine", LazyEngine)
    clear_cache()
    g2p = get_g2p(
        "th",
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )

    assert calls == []
    g2p("ไทย")
    assert calls == [True]
    g2p("ทดสอบ")
    assert calls == [True]
