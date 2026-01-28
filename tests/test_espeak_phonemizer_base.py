import pytest

from kokorog2p.backends.espeak.phonemizer_base import EspeakPhonemizerBase
from kokorog2p.backends.espeak.voice import Voice


class _ResolveDummy(EspeakPhonemizerBase):
    """Concrete subclass for testing _resolve_voice behavior."""

    def __init__(self, voices: list[Voice]) -> None:
        super().__init__()
        self._voices = list(voices)

    @property
    def version(self) -> tuple[int, ...]:
        return (1, 52, 0)

    def set_voice(self, language: str) -> None:
        raise NotImplementedError

    def phonemize(self, text: str, use_tie: bool = False) -> str:
        raise NotImplementedError

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        # For these unit tests we don't care about filtering behavior
        return list(self._voices)


class _PickleDummy(EspeakPhonemizerBase):
    """Concrete subclass for testing __setstate__ calling set_voice()."""

    def __init__(self) -> None:
        super().__init__()
        self.set_voice_calls: list[str] = []

    @property
    def version(self) -> tuple[int, ...]:
        return (0,)

    def set_voice(self, language: str) -> None:
        self.set_voice_calls.append(language)

    def phonemize(self, text: str, use_tie: bool = False) -> str:
        return ""


class TestEspeakPhonemizerBaseHelpers:
    def test_parse_version_string_strips_dev_suffix(self):
        assert EspeakPhonemizerBase._parse_version_string("1.51.1-dev") == (1, 51, 1)
        assert EspeakPhonemizerBase._parse_version_string("1.51.1-dev foo") == (
            1,
            51,
            1,
        )
        assert EspeakPhonemizerBase._parse_version_string("1.50") == (1, 50)

    def test_parse_version_string_handles_garbage(self):
        assert EspeakPhonemizerBase._parse_version_string("") == (0,)
        assert EspeakPhonemizerBase._parse_version_string("n/a") == (0,)

    def test_parse_version_output_extracts_version_and_data_path(self):
        s = "eSpeak NG text-to-speech: 1.50  Data at: /usr/lib/espeak-ng-data\n"
        ver, data = EspeakPhonemizerBase._parse_version_output(s)
        assert ver == (1, 50)
        assert data is not None
        assert data.as_posix().endswith("/usr/lib/espeak-ng-data")

    def test_parse_version_output_handles_no_data_path(self):
        s = "eSpeak NG text-to-speech: 1.52.0\n"
        ver, data = EspeakPhonemizerBase._parse_version_output(s)
        assert ver == (1, 52, 0)
        assert data is None

    def test_resolve_voice_regular_uses_first_seen_identifier_per_language(self):
        voices = [
            Voice(name="A", language="en-us", identifier="en-us"),
            Voice(
                name="B", language="en-us", identifier="en-us-variant"
            ),  # should be ignored
            Voice(name="C", language="en-gb", identifier="en-gb"),
        ]
        d = _ResolveDummy(voices)
        identifier, chosen = d._resolve_voice("en-us")
        assert identifier == "en-us"
        assert chosen.language == "en-us"
        assert chosen.identifier == "en-us"

    def test_resolve_voice_raises_on_invalid(self):
        d = _ResolveDummy([Voice(language="en-us", identifier="en-us")])
        with pytest.raises(RuntimeError):
            d._resolve_voice("")
        with pytest.raises(RuntimeError):
            d._resolve_voice("xx-zz-not-a-lang")

    def test_voice_property_returns_current_voice(self):
        d = _PickleDummy()
        assert d.voice is None
        d._current_voice = Voice(language="en-us", identifier="en-us")
        assert d.voice is not None
        assert d.voice.language == "en-us"

    def test_setstate_calls_set_voice_when_voice_present(self):
        d1 = _PickleDummy()
        d1._version = (1, 50)
        d1._current_voice = Voice(language="en-us", identifier="en-us")
        state = d1.__getstate__()

        d2 = _PickleDummy()
        d2.__setstate__(state)

        assert d2._version == (1, 50)
        assert d2.voice is not None
        assert d2.voice.language == "en-us"
        assert d2.set_voice_calls == ["en-us"]
