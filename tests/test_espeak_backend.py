"""Tests for the espeak-ng backend.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import os
import pickle
import sys

import pytest

from kokorog2p.backends.espeak.api import EspeakLibrary
from kokorog2p.backends.espeak.phonemizer_base import EspeakPhonemizerBase
from kokorog2p.backends.espeak.voice import Voice


@pytest.mark.espeak
class TestEspeakBackend:
    """Tests for the EspeakBackend class."""

    def test_creation(self, espeak_backend, espeak_backend_cli):
        """Test backend creation with default parameters."""
        assert espeak_backend.language == "en-us"
        assert espeak_backend.with_stress is True
        assert espeak_backend.tie == "^"
        assert espeak_backend.use_cli is False
        assert espeak_backend_cli.use_cli is True
        assert espeak_backend_cli.tie == "^"
        assert espeak_backend_cli.with_stress is True
        assert espeak_backend_cli.language == "en-us"

    def test_is_british(self, espeak_backend, espeak_backend_gb):
        """Test British English detection."""
        assert espeak_backend.is_british is False
        assert espeak_backend_gb.is_british is True

    def test_phonemize_word(self, espeak_backend, espeak_backend_cli):
        """Test converting a single word to phonemes."""
        result = espeak_backend.phonemize("hello")
        result_cli = espeak_backend_cli.phonemize("hello")
        assert isinstance(result, str)
        assert len(result) > 0
        assert isinstance(result_cli, str)
        assert len(result_cli) > 0
        assert result == result_cli

    def test_multiple_exclamation_marks(self, espeak_backend):
        """Test converting !!!."""
        result = espeak_backend.phonemize("!!!")
        assert isinstance(result, str)
        assert len(result) == 0

    def test_phonemize_sentence(self, espeak_backend):
        """Test converting a sentence to phonemes."""
        result = espeak_backend.phonemize("Hello world")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_phonemize_with_kokoro(self, espeak_backend, espeak_backend_cli):
        """Test phonemization with Kokoro format conversion."""
        result = espeak_backend.phonemize("say", convert_to_kokoro=True)
        result_cli = espeak_backend_cli.phonemize("say", convert_to_kokoro=True)
        assert isinstance(result, str)
        assert len(result) > 0
        assert result == result_cli

    def test_phonemize_raw_ipa(self, espeak_backend):
        """Test phonemization without Kokoro conversion."""
        result = espeak_backend.phonemize("say", convert_to_kokoro=False)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_phonemize_list(self, espeak_backend):
        """Test batch phonemization."""
        texts = ["hello", "world", "test"]
        results = espeak_backend.phonemize_list(texts)
        assert isinstance(results, list)
        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)

    def test_word_phonemes(self, espeak_backend):
        """Test single word phonemization without separators."""
        result = espeak_backend.word_phonemes("hello")
        assert isinstance(result, str)
        assert "_" not in result

    def test_version_string(self, espeak_backend, espeak_backend_cli):
        """Test version string format."""
        version = espeak_backend.version
        version_cli = espeak_backend_cli.version
        assert isinstance(version, str)
        parts = version.split(".")
        assert len(parts) >= 1
        assert isinstance(version_cli, str)
        parts_cli = version_cli.split(".")
        assert len(parts_cli) >= 1

    def test_repr(self, espeak_backend):
        """Test string representation."""
        result = repr(espeak_backend)
        assert "EspeakBackend" in result
        assert "en-us" in result

    def test_british_phonemization(self, espeak_backend_gb):
        """Test British English phonemization."""
        result = espeak_backend_gb.phonemize("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_remove_punctuation_hyphen_preserved(self, espeak_backend):
        """Test hyphens between letters are preserved."""
        result = espeak_backend.remove_punctuation("my-world")
        assert result == "my-world"

    def test_remove_punctuation_single_quotes_removed(self, espeak_backend):
        """Test single quotes around words are removed."""
        result = espeak_backend.remove_punctuation("'Hello'")
        assert result == "Hello"

    def test_remove_punctuation_double_quotes_removed(self, espeak_backend):
        """Test double quotes around words are removed."""
        result = espeak_backend.remove_punctuation('"Hello"')
        assert result == "Hello"

    def test_remove_punctuation_contraction_preserved(self, espeak_backend):
        """Test apostrophes in contractions are preserved."""
        result = espeak_backend.remove_punctuation("don't")
        assert result == "don't"
        assert "'" in result

    def test_remove_punctuation_possessive_preserved(self, espeak_backend):
        """Test apostrophes in possessives are preserved."""
        result = espeak_backend.remove_punctuation("John's book")
        assert result == "John's book"

    def test_remove_punctuation_collapse_question_marks(self, espeak_backend):
        """Test multiple question marks collapse to one."""
        result = espeak_backend.remove_punctuation("Hello??")
        assert result == "Hello?"

    def test_remove_punctuation_single_question_kept(self, espeak_backend):
        """Test single question mark at end is kept."""
        result = espeak_backend.remove_punctuation("Hello?")
        assert result == "Hello?"

    def test_remove_punctuation_standalone_question_removed(self, espeak_backend):
        """Test standalone question mark is removed."""
        result = espeak_backend.remove_punctuation("?")
        assert result == ""

    def test_remove_punctuation_standalone_exclamation_removed(self, espeak_backend):
        """Test standalone exclamation mark is removed."""
        result = espeak_backend.remove_punctuation("!")
        assert result == ""

    def test_remove_punctuation_trailing_exclamation_after_period(self, espeak_backend):
        """Test trailing exclamation after period is removed."""
        result = espeak_backend.remove_punctuation("I don't like you.!")
        assert result == "I don't like you."

    def test_remove_punctuation_standalone_dots_removed(self, espeak_backend):
        """Test standalone dots are removed."""
        result = espeak_backend.remove_punctuation("..")
        assert result == ""

    def test_remove_punctuation_ellipsis_normalized(self, espeak_backend):
        """Test ellipsis sequences are normalized to single period."""
        result = espeak_backend.remove_punctuation("I like this ... . Hello.")
        assert result == "I like this. Hello."

    def test_remove_punctuation_multiple_contractions(self, espeak_backend):
        """Test multiple contractions are preserved."""
        result = espeak_backend.remove_punctuation("we're sure you're right")
        assert "we're" in result
        assert "you're" in result

    def test_remove_punctuation_special_symbols_preserved(self, espeak_backend):
        """Test special symbols like @ and # are preserved."""
        result = espeak_backend.remove_punctuation("test@example.com #tag")
        assert "@" in result
        assert "#" in result

    def test_remove_punctuation_spacing_enforced(self, espeak_backend):
        """Test space is enforced after punctuation."""
        result = espeak_backend.remove_punctuation("Hello,world")
        assert result == "Hello, world"

    def test_remove_punctuation_collapse_semicolons(self, espeak_backend):
        """Test multiple semicolons collapse to one."""
        result = espeak_backend.remove_punctuation("Hello;;world")
        assert result == "Hello; world"

    def test_remove_punctuation_collapse_colons(self, espeak_backend):
        """Test multiple colons collapse to one."""
        result = espeak_backend.remove_punctuation("Hello::world")
        assert result == "Hello: world"

    def test_remove_punctuation_collapse_exclamations(self, espeak_backend):
        """Test multiple exclamation marks collapse to one."""
        result = espeak_backend.remove_punctuation("Hello!!world")
        assert result == "Hello! world"

    def test_remove_punctuation_abbreviation_period_kept(self, espeak_backend):
        """Test period in abbreviation is kept."""
        result = espeak_backend.remove_punctuation("Dr. Smith")
        assert result == "Dr. Smith"

    def test_remove_punctuation_quotes_with_contraction(self, espeak_backend):
        """Test quotes removed but contractions kept."""
        result = espeak_backend.remove_punctuation("'I don't know'")
        assert "don't" in result
        assert result.count("'") == 1  # Only contraction apostrophe

    def test_remove_punctuation_empty_string(self, espeak_backend):
        """Test empty string handling."""
        result = espeak_backend.remove_punctuation("")
        assert result == ""

    def test_remove_punctuation_complex_sentence(self, espeak_backend):
        """Test complex sentence with mixed punctuation."""
        result = espeak_backend.remove_punctuation(
            "Don't worry, 'they're' happy! What's up??"
        )
        assert "Don't" in result
        assert "they're" in result
        assert "What's" in result
        assert "," in result
        assert "!" in result
        assert result.count("?") == 1  # Only one ?
        # Contraction apostrophes present (don't / they're / what's)
        assert "'" in result

    def test_remove_punctuation_hyphen_compound_words(self, espeak_backend):
        """Test hyphens in compound words are preserved."""
        result = espeak_backend.remove_punctuation("state-of-the-art technology")
        assert result == "state-of-the-art technology"


def test_text_to_phonemes_no_progress_guard():
    """EspeakLibrary should stop when pointer does not advance."""

    class DummyLib:
        def __init__(self) -> None:
            self.calls = 0

            def _func(text_ptr, text_mode, phoneme_mode):
                self.calls += 1
                return b"a"

            self.espeak_TextToPhonemes = _func

    dummy = DummyLib()
    library = EspeakLibrary.__new__(EspeakLibrary)
    library._lib = dummy  # type: ignore[assignment]

    result = library.text_to_phonemes("abc")
    assert result == "a"
    assert dummy.calls == 1


class _DummyBase(EspeakPhonemizerBase):
    """Minimal concrete subclass to unit-test EspeakPhonemizerBase helpers."""

    def __init__(self, voices: list[Voice]) -> None:
        super().__init__()
        self._voices = voices

    @property
    def version(self) -> tuple[int, ...]:
        return (1, 52, 0)

    def set_voice(self, language: str) -> None:
        raise NotImplementedError

    def phonemize(self, text: str, use_tie: bool = False) -> str:
        raise NotImplementedError

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        return list(self._voices)


class TestPhonemizerBaseHelpers:
    """Pure unit tests for shared helper logic (no espeak install required)."""

    def test_parse_version_string_strips_dev_suffix(self):
        assert EspeakPhonemizerBase._parse_version_string("1.51.1-dev") == (1, 51, 1)
        assert EspeakPhonemizerBase._parse_version_string("1.51.1-dev foo") == (
            1,
            51,
            1,
        )
        assert EspeakPhonemizerBase._parse_version_string("1.50") == (1, 50)

    def test_parse_version_output_extracts_data_path(self):
        text = "eSpeak NG text-to-speech: 1.50  Data at: /usr/lib/espeak-ng-data\n"
        ver, data = EspeakPhonemizerBase._parse_version_output(text)
        assert ver == (1, 50)
        assert data is not None
        assert data.as_posix().endswith("/usr/lib/espeak-ng-data")

    def test_resolve_voice_regular_prefers_first_identifier_per_language(self):
        voices = [
            Voice(name="A", language="en-us", identifier="en-us"),
            Voice(
                name="B", language="en-us", identifier="en-us-variant"
            ),  # should be ignored
            Voice(name="C", language="en-gb", identifier="en-gb"),
        ]
        d = _DummyBase(voices)
        identifier, chosen = d._resolve_voice("en-us")
        assert identifier == "en-us"
        assert chosen.language == "en-us"
        assert chosen.identifier == "en-us"

    def test_resolve_voice_raises_on_invalid(self):
        d = _DummyBase([Voice(language="en-us", identifier="en-us")])
        with pytest.raises(RuntimeError):
            d._resolve_voice("")
        with pytest.raises(RuntimeError):
            d._resolve_voice("xx-zz-not-a-lang")


@pytest.mark.espeak
class TestPhonemizer:
    """Tests for the Phonemizer (wrapper) class."""

    def test_version(self, has_espeak):
        """Test version is available."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()
        assert p.version is not None
        assert isinstance(p.version, tuple)
        assert len(p.version) >= 2

    def test_phonemize(self, has_espeak, has_espeak_cli):
        """Test basic phonemization."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import CliPhonemizer, Phonemizer

        p = Phonemizer()
        p.set_voice("en-us")

        result = p.phonemize("hello")
        assert isinstance(result, str)
        assert len(result) > 0
        if has_espeak_cli:
            p2 = CliPhonemizer()
            p2.set_voice("en-us")

            result2 = p2.phonemize("hello")
            assert isinstance(result2, str)
            assert len(result2) > 0
            assert result == result2

    def test_set_voice(self, has_espeak, has_espeak_cli):
        """Test voice selection."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import CliPhonemizer, Phonemizer

        p = Phonemizer()
        p.set_voice("en-us")
        p.set_voice("en-gb")
        if has_espeak_cli:
            p2 = CliPhonemizer()
            p2.set_voice("en-us")
            p2.set_voice("en-gb")
            assert p.phonemize("hello") == p2.phonemize("hello")


@pytest.mark.espeak
class TestVoice:
    """Tests for the Voice class."""

    def test_from_language(self, has_espeak):
        """Test creating voice from language code."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Voice

        voice = Voice.from_language("en-us")
        assert voice.language == "en-us"

        voice_gb = Voice.from_language("en-gb")
        assert voice_gb.language == "en-gb"


@pytest.mark.espeak
class TestVoiceListing:
    """Tests for listing available voices."""

    def test_list_voices(self, has_espeak):
        """Test listing all voices."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()
        voices = p.list_voices()

        assert voices
        assert len(voices) > 0
        languages = {v.language for v in voices}
        assert any(lang.startswith("en") for lang in languages if lang)

    def test_list_voices_filtered(self, has_espeak):
        """Test listing voices with filter."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()
        mbrola = p.list_voices("mbrola")
        espeak = p.list_voices()

        if mbrola:
            espeak_ids = {v.identifier for v in espeak}
            mbrola_ids = {v.identifier for v in mbrola}
            assert not espeak_ids.intersection(mbrola_ids)


@pytest.mark.espeak
class TestVoiceSelection:
    """Tests for voice selection."""

    def test_set_and_get_voice(self, has_espeak):
        """Test setting and retrieving voice."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()
        assert p.voice is None

        p.set_voice("en-us")
        assert p.voice is not None
        assert p.voice.language == "en-us"

        p.set_voice("fr-fr")
        assert p.voice.language == "fr-fr"

    def test_invalid_voice(self, has_espeak):
        """Test error on invalid voice."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()

        with pytest.raises(RuntimeError):
            p.set_voice("")

        with pytest.raises(RuntimeError):
            p.set_voice("nonexistent-xyz")


@pytest.mark.espeak
class TestPickling:
    """Tests for pickle support."""

    def test_pickle_phonemizer(self, has_espeak):
        """Test pickling and unpickling."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p1 = Phonemizer()
        p1.set_voice("en-us")

        data = pickle.dumps(p1)
        p2 = pickle.loads(data)

        assert p1.version == p2.version
        assert p1.library_path == p2.library_path
        assert p1.voice is not None
        assert p2.voice is not None
        assert p1.voice.language == p2.voice.language

    def test_pickle_preserves_results(self, has_espeak):
        """Test pickled instance produces same output."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p1 = Phonemizer()
        p1.set_voice("en-us")
        result1 = p1.phonemize("hello")

        data = pickle.dumps(p1)
        p2 = pickle.loads(data)
        result2 = p2.phonemize("hello")

        assert result1 == result2


@pytest.mark.espeak
class TestMultipleInstances:
    """Tests for multiple phonemizer instances."""

    def test_shared_properties(self, has_espeak):
        """Test instances share some properties."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p1 = Phonemizer()
        p2 = Phonemizer()

        assert p1.version == p2.version
        assert p1.library_path == p2.library_path

    def test_independent_voices(self, has_espeak, has_espeak_cli):
        """Test instances have independent voice selection."""
        if not has_espeak:
            pytest.skip("espeak not available")
        if not has_espeak_cli:
            pytest.skip("espeak CLI not available")

        from kokorog2p.backends.espeak import CliPhonemizer, Phonemizer

        p1 = Phonemizer()
        p2 = Phonemizer()
        p3 = CliPhonemizer()

        p1.set_voice("fr-fr")
        p2.set_voice("en-us")
        p3.set_voice("de")

        assert p1.voice is not None
        assert p2.voice is not None
        assert p3.voice is not None
        assert p1.voice.language == "fr-fr"
        assert p2.voice.language == "en-us"
        assert p3.voice.language == "de"


@pytest.mark.espeak
class TestLibraryInfo:
    """Tests for library information."""

    def test_version_tuple(self, has_espeak, has_espeak_cli):
        """Test version format."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import CliPhonemizer, Phonemizer

        p = Phonemizer()
        assert p.version >= (1, 48)
        assert all(isinstance(v, int) for v in p.version)
        if has_espeak_cli:
            p_cli = CliPhonemizer()
            assert p_cli.version >= (1, 48)
            assert all(isinstance(v, int) for v in p_cli.version)

    def test_library_path(self, has_espeak):
        """Test library path."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()
        assert "espeak" in str(p.library_path)
        assert os.path.isabs(p.library_path)

    def test_data_path(self, has_espeak):
        """Test data path."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()
        assert p.data_path is not None


@pytest.mark.espeak
class TestTieCharacter:
    """Tests for tie character handling."""

    def test_with_separator(self, has_espeak, has_espeak_cli):
        """Test output with separator."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import CliPhonemizer, Phonemizer

        p = Phonemizer()
        p.set_voice("en-us")

        result = p.phonemize("Jackie", use_tie=False)
        assert "_" in result
        if has_espeak_cli:
            p_cli = CliPhonemizer()
            p_cli.set_voice("en-us")

            result = p_cli.phonemize("Jackie", use_tie=False)
            assert "_" in result

    def test_with_tie(self, has_espeak, has_espeak_cli):
        """Test output with tie character."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import CliPhonemizer, Phonemizer

        p = Phonemizer()
        p.set_voice("en-us")

        if p.version >= (1, 49):
            result = p.phonemize("Jackie", use_tie=True)
            assert "͡" in result or "_" not in result
        if has_espeak_cli:
            p_cli = CliPhonemizer()
            p_cli.set_voice("en-us")

            if p_cli.version >= (1, 49):
                result = p_cli.phonemize("Jackie", use_tie=True)
                assert "͡" in result or "_" not in result


@pytest.mark.espeak
@pytest.mark.skipif(sys.platform == "win32", reason="Different on Windows")
class TestTempDirectory:
    """Tests for temporary directory handling."""

    def test_temp_dir_exists(self, has_espeak):
        """Test temp directory exists during use."""
        if not has_espeak:
            pytest.skip("espeak not available")

        import pathlib

        from kokorog2p.backends.espeak import Phonemizer

        p = Phonemizer()
        p.set_voice("en-us")

        assert p._api.temp_dir is not None
        temp_dir = pathlib.Path(p._api.temp_dir)
        assert temp_dir.exists()
        files = list(temp_dir.iterdir())
        assert len(files) >= 1


# Backwards compatibility tests
@pytest.mark.espeak
class TestBackwardsCompatibility:
    """Tests for backwards compatible aliases."""

    def test_espeak_wrapper_alias(self, has_espeak):
        """Test EspeakWrapper alias works."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import EspeakWrapper

        w = EspeakWrapper()
        assert w.version is not None

    def test_espeak_voice_alias(self, has_espeak):
        """Test EspeakVoice alias works."""
        if not has_espeak:
            pytest.skip("espeak not available")

        from kokorog2p.backends.espeak import EspeakVoice

        v = EspeakVoice.from_language("en-us")
        assert v.language == "en-us"
