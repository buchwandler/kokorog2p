"""Opt-in live Goruut smoke tests.

These tests exercise the real pygoruut binary.  They are NEVER run by default.
Activate with:

    KOKOROG2P_RUN_GORUUT_LIVE=1 python -m pytest tests/test_goruut_live.py

CI recommendation: run on one Linux/Python version with `kokorog2p[goruut-direct]`
installed explicitly.  On Termux, run manually.
"""

from __future__ import annotations

import os

import pytest

_LIVE = os.environ.get("KOKOROG2P_RUN_GORUUT_LIVE") == "1"

pytestmark = [
    pytest.mark.external_backend,
    pytest.mark.skipif(
        not _LIVE,
        reason="Set KOKOROG2P_RUN_GORUUT_LIVE=1 to run live Goruut smoke tests",
    ),
]


class TestGoruutLive:
    """Smoke tests against the real Goruut process."""

    def test_basic_english_phonemize(self):
        """One English word returns non-empty phonemes."""
        from kokorog2p import phonemize

        result = phonemize("Hello", language="en-us", backend="goruut")
        assert result.phonemes, f"Expected non-empty phonemes, got: {result.phonemes!r}"

    def test_multi_language_smoke(self):
        """English, French, and German all return non-empty phonemes."""
        from kokorog2p import phonemize

        for language, text in [
            ("en-us", "Hello"),
            ("fr", "Bonjour"),
            ("de", "Hallo"),
        ]:
            result = phonemize(text, language=language, backend="goruut")
            assert result.phonemes, (
                f"{language}: expected non-empty phonemes for {text!r}"
            )
