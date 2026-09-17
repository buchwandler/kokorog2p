"""Tests for eSpeak batch phonemization and preprocessing parity."""

from __future__ import annotations

from typing import ClassVar

import pytest

from kokorog2p.backends.espeak import EspeakBackend
from kokorog2p.backends.espeak import backend as backend_module
from kokorog2p.espeak_g2p import EspeakOnlyG2P


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


class CountingFakeRuntime:
    """Fake runtime that counts phonemize and phonemize_many calls."""

    instances: ClassVar[list[CountingFakeRuntime]] = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.info = FakeInfo()
        self.phonemize_count = 0
        self.phonemize_many_count = 0
        self.last_batch_texts = None
        self.closed = False
        CountingFakeRuntime.instances.append(self)

    def resolve_voice(self, voice: str):
        from espeakng_runtime import Voice

        return Voice(name="English", language=voice, identifier=voice)

    def phonemize(self, text: str, **kwargs) -> str:
        self.phonemize_count += 1
        return "həlˈo͡ʊ"

    def phonemize_many(self, texts, **kwargs) -> list[str]:
        self.phonemize_many_count += 1
        self.last_batch_texts = list(texts)
        return ["həlˈo͡ʊ" for _ in texts]

    def list_voices(self, filter_name=None):
        return []

    def close(self):
        self.closed = True


@pytest.fixture
def counting_runtime(monkeypatch):
    CountingFakeRuntime.instances.clear()
    monkeypatch.setattr(backend_module, "EspeakRuntime", CountingFakeRuntime)
    return CountingFakeRuntime


def test_phonemize_list_delegates_to_phonemize_many(counting_runtime):
    """phonemize_list() should call phonemize_many(), not scalar phonemize()."""
    backend = EspeakBackend("en-us")
    result = backend.phonemize_list(["hello", "world", "test"])
    assert len(result) == 3
    runtime = counting_runtime.instances[0]
    assert runtime.phonemize_many_count == 1
    assert runtime.phonemize_count == 0


def test_preprocessing_parity_with_punctuation(counting_runtime):
    """phonemize_many([x, y]) == [phonemize(x), phonemize(y)]
    with punctuation removal."""
    backend = EspeakBackend("en-us")
    texts = ["Hello, world!", "Test... sentence;"]

    batch_result = backend.phonemize_many(texts, remove_punctuation=True)
    scalar_results = [backend.phonemize(t, remove_punctuation=True) for t in texts]

    assert batch_result == scalar_results


def test_preprocessing_parity_without_punctuation(counting_runtime):
    """phonemize_many([x, y]) == [phonemize(x), phonemize(y)]
    without punctuation removal."""
    backend = EspeakBackend("en-us")
    texts = ["Hello, world!", "Test... sentence;"]

    batch_result = backend.phonemize_many(texts, remove_punctuation=False)
    scalar_results = [backend.phonemize(t, remove_punctuation=False) for t in texts]

    assert batch_result == scalar_results


def test_preprocessing_parity_raw_mode(counting_runtime):
    """phonemize_many([x, y]) == [phonemize(x), phonemize(y)] in raw mode."""
    backend = EspeakBackend("en-us")
    texts = ["Hello, world!", "Test... sentence;"]

    batch_result = backend.phonemize_many(
        texts, convert_to_kokoro=False, remove_punctuation=True
    )
    scalar_results = [
        backend.phonemize(t, convert_to_kokoro=False, remove_punctuation=True)
        for t in texts
    ]

    assert batch_result == scalar_results


def test_espeak_only_g2p_batches_word_calls(monkeypatch):
    """EspeakOnlyG2P.__call__() invokes
    phonemize_many() exactly once for multiple words."""
    CountingFakeRuntime.instances.clear()
    monkeypatch.setattr(backend_module, "EspeakRuntime", CountingFakeRuntime)

    g2p = EspeakOnlyG2P("en-us")
    tokens = g2p("Hello world this is a test")

    runtime = CountingFakeRuntime.instances[0]
    # Should use exactly one batch call. The 1 scalar call is from _validate_backend().
    assert runtime.phonemize_many_count == 1
    # validate_backend calls phonemize once; no additional scalar calls for words.
    assert runtime.phonemize_count == 1  # validation only
    # Should have produced tokens for all 6 words.
    word_tokens = [t for t in tokens if t.tag != "PUNCT"]
    assert len(word_tokens) == 6


def test_espeak_only_g2p_preserves_punctuation_tokens(monkeypatch):
    """Punctuation tokens should be preserved without phonemization calls."""
    CountingFakeRuntime.instances.clear()
    monkeypatch.setattr(backend_module, "EspeakRuntime", CountingFakeRuntime)

    g2p = EspeakOnlyG2P("en-us")
    tokens = g2p("Hello, world!")

    punct_tokens = [t for t in tokens if t.tag == "PUNCT"]
    assert len(punct_tokens) == 2
    assert punct_tokens[0].text == ","
    assert punct_tokens[1].text == "!"
    # Punctuation phonemes should be the text itself.
    assert punct_tokens[0].phonemes == ","
    assert punct_tokens[1].phonemes == "!"


def test_espeak_only_g2p_empty_input(monkeypatch):
    """Empty input should return no tokens without calling the runtime."""
    CountingFakeRuntime.instances.clear()
    monkeypatch.setattr(backend_module, "EspeakRuntime", CountingFakeRuntime)

    g2p = EspeakOnlyG2P("en-us")
    assert g2p("") == []
    assert g2p("   ") == []
    assert len(CountingFakeRuntime.instances) == 0
