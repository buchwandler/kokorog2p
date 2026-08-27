from pathlib import Path

import pytest

from kokorog2p.ru.engine import (
    RussianEspeakEngine,
    RussianEspeakError,
    clear_stress_probe_cache,
    supports_combining_acute,
)


class FakeBackend:
    language = "ru"
    data_path = Path("/tmp/fake-espeak")

    def phonemize(self, text, *, convert_to_kokoro=True, remove_punctuation=True):
        return "a" if "за́мок" in text else "o"


def test_combining_acute_probe_is_behavioral_and_cached():
    clear_stress_probe_cache()
    backend = FakeBackend()
    assert supports_combining_acute(
        type(
            "Adapter",
            (),
            {"phonemize_marked": lambda self, text: backend.phonemize(text)},
        )()
    )
    engine = RussianEspeakEngine(backend=backend, strict_stress=True)
    assert engine.phonemize_marked("слово") == "o"


def test_strict_engine_rejects_backend_without_acute_support():
    class FlatBackend(FakeBackend):
        def phonemize(self, text, **kwargs):
            return "same"

    clear_stress_probe_cache()
    with pytest.raises(RussianEspeakError, match="combining-acute"):
        RussianEspeakEngine(backend=FlatBackend(), strict_stress=True)


def test_non_strict_engine_can_use_backend_without_probe_support():
    class FlatBackend(FakeBackend):
        def phonemize(self, text, **kwargs):
            return "same"

    engine = RussianEspeakEngine(backend=FlatBackend(), strict_stress=False)
    assert engine.phonemize_marked("слово") == "same"
