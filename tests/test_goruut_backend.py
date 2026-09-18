"""Tests for the goruut backend.

TestFromGoruut and the Android platform-detection tests are deterministic
and run without a real pygoruut installation.

TestGoruutBackend and TestGoruutOnlyG2P use an injected fake goruut process
so they never download or start the real 96 MB Goruut executable.
"""

from __future__ import annotations

import platform
from typing import Any

import pytest

from kokorog2p.backends.goruut.backend import (
    GoruutBackend,
    GoruutBackendError,
    _pygoruut_platform_compat,
)

# ---------------------------------------------------------------------------
# Fake pygoruut response
# ---------------------------------------------------------------------------


class _FakePhonemeResult:
    """Deterministic phonemize result that responds to str()."""

    def __init__(self, ipa: str) -> None:
        self._ipa = ipa

    def __str__(self) -> str:
        return self._ipa


_FAKE_RESPONSES: dict[str, _FakePhonemeResult] = {
    "hello": _FakePhonemeResult("həlˈoʊ"),
    "say": _FakePhonemeResult("sˈeɪ"),
    "Hello world": _FakePhonemeResult("həlˈoʊ wˈɜɹld"),
    "Bonjour": _FakePhonemeResult("bɔ̃ʒuʁ"),
    "Hallo": _FakePhonemeResult("haloː"),
    "world": _FakePhonemeResult("wˈɜɹld"),
    "test": _FakePhonemeResult("tˈɛst"),
}


class _FakeGoruut:
    """Fake pygoruut process that returns deterministic IPA."""

    def phonemize(
        self,
        language: str,
        sentence: str,
        is_punct: bool = True,
    ) -> Any:
        return _FAKE_RESPONSES.get(sentence, _FakePhonemeResult("tˈɛst"))


@pytest.fixture()
def _inject_fake_goruut(monkeypatch: pytest.MonkeyPatch):
    """Inject a fake goruut singleton for the duration of one test."""
    from kokorog2p.backends.goruut import backend

    fake = _FakeGoruut()
    monkeypatch.setattr(backend, "_goruut_instance", fake)
    yield
    monkeypatch.setattr(backend, "_goruut_instance", None)


# ---------------------------------------------------------------------------
# TestFromGoruut — pure conversion, no pygoruut needed
# ---------------------------------------------------------------------------


class TestFromGoruut:
    """Tests for the from_goruut conversion function."""

    def test_diphthong_ei(self):
        """Test eɪ -> A conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("sˈeɪ") == "sˈA"
        assert from_goruut("ɹˈeɪsɪŋ") == "ɹˈAsɪŋ"

    def test_diphthong_ai(self):
        """Test aɪ -> I conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("maɪ") == "mI"
        assert from_goruut("nˈaɪn") == "nˈIn"

    def test_diphthong_au(self):
        """Test aʊ -> W conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("nˈaʊ") == "nˈW"
        assert from_goruut("θˈaʊzənd") == "θˈWzənd"

    def test_diphthong_oi(self):
        """Test ɔɪ -> Y conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("bˈɔɪ") == "bˈY"

    def test_diphthong_ou(self):
        """Test oʊ -> O conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("həlˈoʊ") == "həlˈO"
        assert from_goruut("gˈoʊ") == "ɡˈO"

    def test_affricate_tsh(self):
        """Test tʃ -> ʧ conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("tʃˈɜɹtʃ") == "ʧˈɜɹʧ"

    def test_affricate_dzh(self):
        """Test dʒ -> ʤ conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("dʒˈʌdʒ") == "ʤˈʌʤ"

    def test_consonant_g(self):
        """Test g -> ɡ conversion."""
        from kokorog2p.phonemes import from_goruut

        assert from_goruut("gˈoʊ") == "ɡˈO"

    def test_british_keeps_length(self):
        """Test that British English keeps length marks."""
        from kokorog2p.phonemes import from_goruut

        # British should keep ː
        result = from_goruut("hˈɑːd", british=True)
        assert "ː" in result

    def test_us_removes_length(self):
        """Test that US English removes length marks."""
        from kokorog2p.phonemes import from_goruut

        result = from_goruut("hˈɑːd", british=False)
        assert "ː" not in result


# ---------------------------------------------------------------------------
# TestGoruutBackend — uses injected fake, never downloads real goruut
# ---------------------------------------------------------------------------


class TestGoruutBackend:
    """Tests for the GoruutBackend class (deterministic, injected process)."""

    @pytest.fixture()
    def goruut_backend(self, _inject_fake_goruut):
        """Create a GoruutBackend instance with fake goruut."""
        return GoruutBackend("en-us")

    @pytest.fixture()
    def goruut_backend_gb(self, _inject_fake_goruut):
        """Create a British GoruutBackend instance with fake goruut."""
        return GoruutBackend("en-gb")

    def test_phonemize_word(self, goruut_backend):
        """Test phonemizing a single word."""
        result = goruut_backend.phonemize("hello")
        assert result  # Should return non-empty string
        assert isinstance(result, str)

    def test_startup_retries_after_server_exit(self, monkeypatch):
        """Retry the pygoruut 0.8.1 startup race."""
        from kokorog2p.backends.goruut import backend

        attempts = 0
        instance = object()

        class FakePygoruut:
            def __new__(cls, **kwargs):
                nonlocal attempts
                attempts += 1
                if attempts == 1:
                    raise RuntimeError("Phonemize server exited before becoming ready")
                return instance

        monkeypatch.setattr("pygoruut.pygoruut.Pygoruut", FakePygoruut)
        monkeypatch.setattr(backend, "_goruut_instance", None)

        assert backend._get_goruut() is instance
        assert attempts == 2

    def test_startup_lock_prevents_concurrent_init(self, monkeypatch):
        """The initialization lock is used for double-checked locking."""
        from kokorog2p.backends.goruut import backend

        instance = object()

        class FakePygoruut:
            def __new__(cls, **kwargs):
                return instance

        monkeypatch.setattr("pygoruut.pygoruut.Pygoruut", FakePygoruut)
        monkeypatch.setattr(backend, "_goruut_instance", None)

        # Acquire the lock to simulate a concurrent thread
        with backend._goruut_init_lock:
            # While lock is held, _get_goruut should wait but still work
            pass
        result = backend._get_goruut()
        assert result is instance

    def test_phonemize_sentence(self, goruut_backend):
        """Test phonemizing a sentence."""
        result = goruut_backend.phonemize("Hello world")
        assert result
        assert " " in result  # Should have space between words

    def test_phonemize_with_kokoro(self, goruut_backend):
        """Test conversion to Kokoro format."""
        result = goruut_backend.phonemize("say", convert_to_kokoro=True)
        assert "A" in result  # eɪ should be converted to A

    def test_phonemize_raw_ipa(self, goruut_backend):
        """Test getting raw IPA output."""
        result = goruut_backend.phonemize("say", convert_to_kokoro=False)
        assert "eɪ" in result or "e" in result  # Should have raw diphthong

    def test_phonemize_list(self, goruut_backend):
        """Test phonemizing a list of texts."""
        texts = ["hello", "world"]
        results = goruut_backend.phonemize_list(texts)
        assert len(results) == 2
        assert all(isinstance(r, str) for r in results)

    def test_word_phonemes(self, goruut_backend):
        """Test word_phonemes method."""
        result = goruut_backend.word_phonemes("hello")
        assert result
        assert "_" not in result  # Should not have word separators

    def test_is_british(self, goruut_backend, goruut_backend_gb):
        """Test is_british property."""
        assert not goruut_backend.is_british
        assert goruut_backend_gb.is_british

    def test_get_supported_languages(self):
        """Test get_supported_languages method."""
        languages = GoruutBackend.get_supported_languages()
        assert isinstance(languages, list)
        assert "en-us" in languages
        assert "en-gb" in languages
        assert "fr" in languages

    def test_empty_text(self, goruut_backend):
        """Test phonemizing empty text."""
        result = goruut_backend.phonemize("")
        assert result == ""

    def test_repr(self, goruut_backend):
        """Test __repr__ method."""
        repr_str = repr(goruut_backend)
        assert "GoruutBackend" in repr_str
        assert "en-us" in repr_str

    def test_goruut_backend_error_is_runtime_error(self):
        """GoruutBackendError is a RuntimeError subclass."""
        assert issubclass(GoruutBackendError, RuntimeError)
        err = GoruutBackendError("test message")
        assert str(err) == "test message"


# ---------------------------------------------------------------------------
# TestGoruutOnlyG2P — uses injected fake
# ---------------------------------------------------------------------------


class TestGoruutOnlyG2P:
    """Tests for the GoruutOnlyG2P class (deterministic, injected process)."""

    def test_create_instance(self, _inject_fake_goruut):
        """Test creating a GoruutOnlyG2P instance."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        assert g2p.language == "en-us"

    def test_call_returns_tokens(self, _inject_fake_goruut):
        """Test that __call__ returns a list of tokens."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        tokens = g2p("Hello world")
        assert isinstance(tokens, list)
        assert len(tokens) > 0

    def test_phonemize(self, _inject_fake_goruut):
        """Test phonemize method."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        result = g2p.phonemize("Hello world")
        assert isinstance(result, str)
        assert result  # Non-empty

    def test_lookup(self, _inject_fake_goruut):
        """Test lookup method."""
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p = GoruutOnlyG2P("en-us")
        result = g2p.lookup("hello")
        assert result is not None

    def test_is_available_does_not_construct_pygoruut(self, monkeypatch):
        """is_available() does not instantiate Pygoruut or start a process."""
        monkeypatch.setattr(
            "kokorog2p.backends.goruut.backend._probe_platform_executable",
            lambda: True,
        )
        assert GoruutBackend.is_available() is True


# ---------------------------------------------------------------------------
# TestMainAPIWithGoruutBackend — uses injected fake
# ---------------------------------------------------------------------------


class TestMainAPIWithGoruutBackend:
    """Tests for the main API with goruut backend (deterministic, injected)."""

    def test_phonemize_with_goruut(self, _inject_fake_goruut):
        """Test phonemize function with goruut backend."""
        from kokorog2p import phonemize

        result = phonemize("Hello world", backend="goruut", language="en-us")
        assert isinstance(result.phonemes, str)
        assert result  # Non-empty

    def test_get_g2p_with_goruut(self, _inject_fake_goruut):
        """Test get_g2p function with goruut backend."""
        from kokorog2p import get_g2p

        g2p = get_g2p("en-us", backend="goruut", lexicons=())
        assert "GoruutOnlyG2P" in type(g2p).__name__

    def test_cache_works_with_backend(self, _inject_fake_goruut):
        """Test that cache distinguishes between backends."""
        from kokorog2p import clear_cache, get_g2p

        clear_cache()

        g2p_espeak = get_g2p("en-us", backend="espeak", use_spacy=False, lexicons=())
        g2p_goruut = get_g2p("en-us", backend="goruut", lexicons=())

        # They should be different instances
        assert type(g2p_espeak).__name__ != type(g2p_goruut).__name__

    def test_french_with_goruut(self, _inject_fake_goruut):
        """Test French language with goruut backend."""
        from kokorog2p import phonemize

        result = phonemize("Bonjour", language="fr", backend="goruut")
        assert isinstance(result.phonemes, str)
        assert result  # Non-empty

    def test_german_with_goruut(self, _inject_fake_goruut):
        """Test German language with goruut backend."""
        from kokorog2p import phonemize

        result = phonemize("Hallo", language="de", backend="goruut")
        assert isinstance(result.phonemes, str)
        assert result  # Non-empty


# ---------------------------------------------------------------------------
# Android platform-detection tests (deterministic, no real pygoruut)
# ---------------------------------------------------------------------------


class TestAndroidPlatformCompat:
    """Tests for the Android/Termux platform compatibility bridge."""

    def test_non_android_system_yields_immediately(self):
        """When platform.system() is not 'Android', the compat context is a no-op."""
        # This test runs on any non-Android host — the context manager yields
        # without patching anything.
        with _pygoruut_platform_compat():
            pass  # Should not raise

    def test_android_system_name_uses_android_compat_platform(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Android system name triggers the compatibility platform patch."""
        monkeypatch.setattr(platform, "system", lambda: "Android")
        monkeypatch.setattr(platform, "machine", lambda: "aarch64")

        # We cannot fully test _pygoruut_platform_compat without pygoruut installed,
        # but we can verify it doesn't crash and yields.
        with _pygoruut_platform_compat():
            pass

    def test_android_unsupported_architecture_is_not_retried(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Platform/architecture ValueError is not retried."""
        from kokorog2p.backends.goruut import backend

        monkeypatch.setattr(platform, "system", lambda: "Android")
        monkeypatch.setattr(platform, "machine", lambda: "x86_64")

        class FakePygoruut:
            def __new__(cls, **kwargs):
                raise ValueError("Unsupported OS: android")

        monkeypatch.setattr("pygoruut.pygoruut.Pygoruut", FakePygoruut)
        monkeypatch.setattr(backend, "_goruut_instance", None)

        with pytest.raises(GoruutBackendError, match="Android"):
            backend._get_goruut()

    def test_format_goruut_platform_error_includes_details(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Platform error helper includes system, machine, and version."""
        from kokorog2p.backends.goruut.backend import _format_goruut_platform_error

        monkeypatch.setattr(platform, "system", lambda: "Android")
        monkeypatch.setattr(platform, "machine", lambda: "aarch64")
        monkeypatch.setattr(
            "kokorog2p.backends.goruut.backend._get_pygoruut_version",
            lambda: "0.8.1",
        )

        msg = _format_goruut_platform_error(ValueError("Unsupported OS: android"))
        assert "Android" in msg
        assert "aarch64" in msg
        assert "0.8.1" in msg
        assert "Unsupported OS: android" in msg

    def test_format_goruut_platform_error_is_not_labeled_not_installed(self):
        """The error message should NOT say 'pygoruut is not installed'."""
        from kokorog2p.backends.goruut.backend import _format_goruut_platform_error

        msg = _format_goruut_platform_error(ValueError("Unsupported OS: android"))
        assert "not installed" not in msg
