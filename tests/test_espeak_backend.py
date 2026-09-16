"""Tests for the runtime-backed direct eSpeak adapter."""

from __future__ import annotations

import pickle
from typing import ClassVar

import pytest
from espeakng_runtime import Voice

from kokorog2p.backends.espeak import CliPhonemizer, EspeakBackend, Phonemizer
from kokorog2p.backends.espeak import backend as backend_module


class FakeInfo:
    requested_mode = "auto"
    implementation = "native"
    executable = "/usr/bin/espeak-ng"
    library = "/usr/lib/libespeak-ng.so"
    data = "/usr/share/espeak-ng-data"
    source = "fake"
    version = "1.52.0"
    exact_clause_api = False
    parity = "best-effort"
    fallback_reason = None
    fallback_code = None

    @property
    def version_tuple(self) -> tuple[int, ...]:
        return (1, 52, 0)


class FakeRuntime:
    instances: ClassVar[list[FakeRuntime]] = []
    fallback = False

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.info = FakeInfo()
        if self.fallback:
            self.info.implementation = "cli"
            self.info.fallback_code = "native-init-failed"
            self.info.fallback_reason = "native setup failed"
        self.closed = False
        self.voices = [Voice(name="English", language="en-us", identifier="en-us")]
        self.instances.append(self)

    def resolve_voice(self, voice: str) -> Voice:
        if voice == "en-gb":
            return Voice(name="English", language="en-gb", identifier="en")
        return Voice(name="English", language=voice, identifier=voice)

    def phonemize(self, text: str, **kwargs) -> str:
        self.last_call = (text, kwargs)
        return "həlˈo͡ʊ"

    def phonemize_many(self, texts, **kwargs) -> list[str]:
        self.last_batch = (list(texts), kwargs)
        return ["həlˈo͡ʊ" for _ in texts]

    def list_voices(self, filter_name=None):
        return self.voices

    def close(self):
        self.closed = True


@pytest.fixture
def fake_runtime(monkeypatch):
    FakeRuntime.instances.clear()
    FakeRuntime.fallback = False
    monkeypatch.setattr(backend_module, "EspeakRuntime", FakeRuntime)
    return FakeRuntime


def test_info_and_runtime_info_are_lazy(fake_runtime):
    backend = EspeakBackend("en-us", data_path="/tmp/data")

    assert backend.info.implementation == "uninitialized"
    assert backend.info.data_path == "/tmp/data"
    assert backend.runtime_info is None
    assert not fake_runtime.instances

    backend.phonemize("hello", convert_to_kokoro=False)

    assert backend.runtime_info is not None
    assert backend.info.implementation == "native"


def test_runtime_construction_forwards_legacy_overrides(fake_runtime, monkeypatch):
    monkeypatch.setenv("KOKOROG2P_ESPEAK_EXECUTABLE", "/custom/espeak")
    monkeypatch.setenv("KOKOROG2P_ESPEAK_LIBRARY", "/custom/lib.so")
    monkeypatch.setenv("KOKOROG2P_ESPEAK_DATA", "/custom/data")

    EspeakBackend("en-us").phonemize("hello", convert_to_kokoro=False)

    assert fake_runtime.instances[0].kwargs == {
        "mode": "auto",
        "executable": "/custom/espeak",
        "library": "/custom/lib.so",
        "data": "/custom/data",
    }


def test_explicit_data_path_precedes_legacy_data(fake_runtime, monkeypatch):
    monkeypatch.setenv("KOKOROG2P_ESPEAK_DATA", "/legacy/data")
    EspeakBackend("en-us", data_path="/explicit/data").phonemize("hello")
    assert fake_runtime.instances[0].kwargs["data"] == "/explicit/data"


def test_cli_mode_and_tie_options(fake_runtime):
    backend = EspeakBackend("en-us", use_cli=True, tie="^")
    backend.phonemize("hello", convert_to_kokoro=False)

    runtime = fake_runtime.instances[0]
    assert runtime.kwargs["mode"] == "cli"
    assert runtime.last_call[1] == {
        "voice": "en-us",
        "separator": None,
        "use_tie": True,
        "tie_char": "͡",
    }


def test_non_tie_mode_uses_separator(fake_runtime):
    backend = EspeakBackend("en-us", tie="_")
    backend.phonemize("hello", convert_to_kokoro=False)
    assert fake_runtime.instances[0].last_call[1]["separator"] == "_"
    assert fake_runtime.instances[0].last_call[1]["use_tie"] is False


def test_batch_and_word_conversion(fake_runtime):
    backend = EspeakBackend("en-us")
    result = backend.phonemize_many(["hello", "world"])
    assert len(result) == 2
    assert backend.word_phonemes("hello")
    assert fake_runtime.instances[0].last_batch[0] == ["hello", "world"]


def test_auto_fallback_is_exposed_as_compatibility_error(fake_runtime):
    fake_runtime.fallback = True
    backend = EspeakBackend("en-us")
    backend.phonemize("hello", convert_to_kokoro=False)
    assert backend.info.implementation == "cli"
    assert backend.native_error is not None
    assert backend.info.native_error_type == "RuntimeError"


def test_close_is_idempotent_and_allows_recreation(fake_runtime):
    backend = EspeakBackend("en-us")
    backend.phonemize("hello")
    first = fake_runtime.instances[0]
    backend.close()
    backend.close()
    assert first.closed
    backend.phonemize("hello")
    assert len(fake_runtime.instances) == 2


def test_backend_pickle_drops_runtime(fake_runtime):
    backend = EspeakBackend("en-us")
    backend.phonemize("hello")
    restored = pickle.loads(pickle.dumps(backend))
    assert restored.runtime_info is None
    assert restored.language == "en-us"


def test_en_gb_uses_requested_voice(fake_runtime):
    backend = EspeakBackend("en-gb")
    backend.phonemize("hello", convert_to_kokoro=False)
    assert fake_runtime.instances[0].last_call[1]["voice"] == "en-gb"


@pytest.mark.espeak
def test_real_runtime_auto_smoke():
    backend = EspeakBackend("en-us")
    try:
        assert backend.phonemize("hello")
        assert backend.runtime_info is not None
    finally:
        backend.close()


@pytest.mark.espeak
def test_real_runtime_cli_smoke():
    backend = EspeakBackend("en-us", use_cli=True)
    try:
        assert backend.phonemize("hello")
    finally:
        backend.close()


def test_compatibility_facades_support_voice_and_pickle(fake_runtime, monkeypatch):
    monkeypatch.setattr("kokorog2p.backends.espeak.compat.EspeakRuntime", FakeRuntime)
    phonemizer = Phonemizer()
    phonemizer.set_voice("en-us")
    assert phonemizer.voice_language == "en-us"
    assert phonemizer.phonemize("hello")
    restored = pickle.loads(pickle.dumps(phonemizer))
    assert restored.voice is not None
    assert restored.phonemize("hello")


def test_cli_compatibility_facade_selects_cli(fake_runtime, monkeypatch):
    monkeypatch.setattr("kokorog2p.backends.espeak.compat.EspeakRuntime", FakeRuntime)
    phonemizer = CliPhonemizer("en-us")
    phonemizer.set_voice("en-us")
    phonemizer.phonemize("hello")
    assert fake_runtime.instances[-1].kwargs["mode"] == "cli"
