"""Tests for the retained eSpeak compatibility interface."""

from __future__ import annotations

from kokorog2p.backends.espeak.phonemizer_base import EspeakPhonemizerBase
from kokorog2p.backends.espeak.voice import Voice


class DummyPhonemizer(EspeakPhonemizerBase):
    @property
    def version(self) -> tuple[int, ...]:
        return (1, 52, 0)

    def set_voice(self, language: str) -> None:
        self._selected = Voice(name="", language=language, identifier=language)

    @property
    def voice(self) -> Voice | None:
        return getattr(self, "_selected", None)

    def phonemize(self, text: str, use_tie: bool = False) -> str:
        return text


def test_minimal_compatibility_interface_supports_batching_and_voice():
    phonemizer = DummyPhonemizer()
    phonemizer.set_voice("en-us")
    assert phonemizer.version == (1, 52, 0)
    assert phonemizer.voice_language == "en-us"
    assert phonemizer.phonemize_many(["hello", "world"]) == ["hello", "world"]


def test_base_does_not_provide_low_level_discovery():
    phonemizer = DummyPhonemizer()
    assert phonemizer.library_path is None
    assert phonemizer.data_path is None
