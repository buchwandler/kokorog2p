"""Structural regression tests for German Gold performance work."""

from __future__ import annotations

import subprocess

import pytest


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
    try:
        words = ["Haus", "weiß", "Klein", "Mutter-kind", ""]
        expected = [phonemizer.phonemize(word) for word in words]
        assert phonemizer.phonemize_many(words) == expected
    finally:
        phonemizer.close()


@pytest.mark.espeak
def test_cli_batch_uses_one_phonemization_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from kokorog2p.backends.espeak.cli_wrapper import CliPhonemizer

    if not CliPhonemizer.is_available():
        pytest.skip("espeak CLI not available")
    phonemizer = CliPhonemizer(language="de")
    calls = 0
    original_run = subprocess.run

    def counted_run(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        return original_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", counted_run)
    try:
        assert phonemizer.phonemize_many(["Haus", "weiß", "Klein"])
    finally:
        phonemizer.close()
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
