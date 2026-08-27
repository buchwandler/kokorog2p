"""Tests for the dependency-isolated Thai engine adapter."""

from types import SimpleNamespace

import pytest

from kokorog2p.th.engine import ThaiEngine


class FakeThai:
    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.calls: list[str] = []
        self.nlp = SimpleNamespace(th2ipa=self.th2ipa)

    def th2ipa(self, text: str) -> str:
        self.calls.append(text)
        if text in self.failures:
            raise RuntimeError("simulated TLTK failure")
        if text == "empty":
            return ""
        return "a2"


class FakeThaiNLP:
    @staticmethod
    def syllable_tokenize(text: str) -> list[str]:
        return text.split()

    @staticmethod
    def word_tokenize(text: str) -> list[str]:
        return text.split()


def test_engine_recovers_a_failed_middle_unit() -> None:
    tltk = FakeThai({"ซ้าย กลาง ขวา", "กลาง"})
    engine = ThaiEngine(tltk_module=tltk, pythainlp_module=FakeThaiNLP)

    result = engine.pronounce_thai_chunk("ซ้าย กลาง ขวา")

    assert result.used_fallback
    assert result.phonemes == "a˩ a˩"
    assert result.unrecovered == ["กลาง"]
    assert any("TH_UNRECOVERED_WORD" in warning for warning in result.warnings)
    assert tltk.calls == ["ซ้าย กลาง ขวา", "ซ้าย", "กลาง", "ขวา"]


def test_engine_recovers_empty_output() -> None:
    tltk = FakeThai({"empty all", "empty"})
    engine = ThaiEngine(tltk_module=tltk, pythainlp_module=FakeThaiNLP)

    result = engine.pronounce_thai_chunk("empty all")

    assert result.used_fallback
    assert result.unrecovered == ["empty"]
    assert result.phonemes == "a˩"


def test_engine_retries_an_obviously_truncated_chunk() -> None:
    tltk = FakeThai()
    engine = ThaiEngine(tltk_module=tltk, pythainlp_module=FakeThaiNLP)
    result = engine.pronounce_thai_chunk("หนึ่ง สอง สาม")
    assert result.used_fallback
    assert result.phonemes == "a˩ a˩ a˩"


def test_missing_dependencies_have_an_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(__import__("sys").modules, "tltk", None)
    with pytest.raises(ImportError, match=r"kokorog2p\[th\]"):
        ThaiEngine()
