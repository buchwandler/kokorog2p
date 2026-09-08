"""Structural regression tests for German Gold performance work."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import kokorog2p.backends.espeak.backend as backend_module
from kokorog2p.backends.espeak.backend import EspeakBackend


@dataclass
class _FakeCli:
    language: str = "de"
    executable: str = "fake-espeak"
    data_path: object | None = None
    voice: object = object()

    def __init__(
        self,
        language: str = "de",
        tie_char: str = "^",
        data_path: object = None,
    ):
        del tie_char
        self.language = language
        self.data_path = data_path
        self.voice = object()

    def set_voice(self, language: str) -> None:
        self.language = language


@pytest.fixture
def failing_native(monkeypatch: pytest.MonkeyPatch):
    class _FailingNative:
        def __init__(self, *args: object, **kwargs: object) -> None:
            del args, kwargs
            raise OSError("native library unavailable")

    monkeypatch.setattr(backend_module, "Phonemizer", _FailingNative)
    monkeypatch.setattr(backend_module, "CliPhonemizer", _FakeCli)


def test_native_downgrade_preserves_diagnostic(failing_native) -> None:
    backend = EspeakBackend(language="de")
    assert backend.info.implementation == "uninitialized"

    _ = backend.wrapper

    assert backend.info.implementation == "cli"
    assert backend.native_error is not None
    assert backend.info.native_error_type == "OSError"
    assert backend.info.native_error == "native library unavailable"


def test_explicit_cli_does_not_construct_native(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _UnexpectedNative:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("native backend must not be constructed in CLI mode")

    monkeypatch.setattr(backend_module, "Phonemizer", _UnexpectedNative)
    monkeypatch.setattr(backend_module, "CliPhonemizer", _FakeCli)

    backend = EspeakBackend(language="de", use_cli=True)
    _ = backend.wrapper

    assert backend.info.implementation == "cli"
    assert backend.native_error is None


def test_german_diagnostics_are_opt_in() -> None:
    from kokorog2p.de import GermanG2P, capture_diagnostics

    g2p = GermanG2P(
        lexicons=("gold",),
        use_espeak_fallback=False,
        use_spacy=False,
    )
    try:
        tokens = g2p("Haus OOV")
        assert tokens
        with capture_diagnostics(max_slow_tokens=1) as stats:
            g2p("Haus OOV")
        assert stats.words == 2
        assert stats.lexicon_calls == 1
        assert stats.lexicon_hits == 1
        assert stats.lexicon_misses == 1
        assert stats.rule_calls == 1
        assert stats.source_counts["lexicon"] == 1
        assert stats.source_counts["german_rules"] == 1
        assert len(stats.slow_tokens) == 1
    finally:
        g2p.close()


@pytest.mark.espeak
def test_cli_batch_preserves_single_word_parity() -> None:
    from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer

    if not CliPhonemizer.is_available():
        pytest.skip("espeak CLI not available")
    phonemizer = CliPhonemizer(language="de")
    words = ["Haus", "weiß", "Klein", "Mutter-kind", ""]
    expected = [phonemizer.phonemize(word) for word in words]
    assert phonemizer.phonemize_many(words) == expected


@pytest.mark.espeak
def test_cli_batch_uses_one_phonemization_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer

    if not CliPhonemizer.is_available():
        pytest.skip("espeak CLI not available")
    phonemizer = CliPhonemizer(language="de")
    import subprocess

    original_run = subprocess.run
    calls = 0

    def counted_run(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", counted_run)
    assert phonemizer.phonemize_many(["Haus", "weiß", "Klein"])
    assert calls == 1

def test_german_fallback_uses_lexphon_provider_backend() -> None:
    from kokorog2p.de import GermanG2P

    g2p = GermanG2P(
        lexicons=("gold",),
        use_espeak_fallback=True,
        use_spacy=False,
    )
    try:
        backend = g2p.pronunciation_backend
        assert backend is not None
        assert backend._backend.fallback_provider == "espeak"
    finally:
        g2p.close()
