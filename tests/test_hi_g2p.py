"""Unit tests for the Hindi eSpeak frontend."""

from dataclasses import dataclass

import pytest

from kokorog2p.hi import HindiG2P
from kokorog2p.hi.model_profile import HindiVocabularyError


@dataclass
class FakeBackend:
    word_output: str = "nəmˈʌsteː"
    text_output: str = "nəmˈʌsteː dˈʊnɪjˌaː"

    def __post_init__(self) -> None:
        self.word_calls: list[tuple[str, bool]] = []
        self.text_calls: list[tuple[str, bool]] = []

    def word_phonemes(self, word: str, convert_to_kokoro: bool = True) -> str:
        self.word_calls.append((word, convert_to_kokoro))
        return self.word_output

    def phonemize(self, text: str, convert_to_kokoro: bool = True) -> str:
        self.text_calls.append((text, convert_to_kokoro))
        return self.text_output


def make_g2p(backend: FakeBackend, *, strict: bool = True) -> HindiG2P:
    g2p = HindiG2P(strict=strict)
    g2p._espeak_backend = backend
    return g2p


def test_aliases_and_metadata() -> None:
    g2p = HindiG2P(language="hindi")
    assert g2p.language == "hi-in"
    assert g2p.get_target_model() == "1.0"
    assert g2p.capabilities() == {
        "language": "hi-in",
        "native": True,
        "engine": "espeak-ng",
        "version": "1.0",
        "target_model": "1.0",
        "runtime_lexicon": False,
        "source_aligned": True,
        "raw_ipa": True,
    }


def test_word_processing_requests_raw_ipa() -> None:
    backend = FakeBackend()
    assert make_g2p(backend).lookup("नमस्ते") == "nəmˈʌsteː"
    assert backend.word_calls == [("नमस्ते", False)]


def test_text_processing_requests_raw_ipa() -> None:
    backend = FakeBackend()
    assert make_g2p(backend).phonemize("नमस्ते दुनिया") == "nəmˈʌsteː dˈʊnɪjˌaː"
    assert backend.text_calls == [("नमस्ते दुनिया", False)]


def test_raw_symbols_are_not_english_converted() -> None:
    raw = "e eː aː ɾ ʋ ʰ ̃"
    assert make_g2p(FakeBackend(word_output=raw)).lookup("fixture") == raw


def test_tokens_preserve_punctuation_whitespace_and_offsets() -> None:
    g2p = make_g2p(FakeBackend())
    text = "नमस्ते, दुनिया!"
    tokens = g2p(text)
    assert [(token.text, token.whitespace) for token in tokens] == [
        ("नमस्ते", ""),
        (",", " "),
        ("दुनिया", ""),
        ("!", ""),
    ]
    assert [(token.get("char_start"), token.get("char_end")) for token in tokens] == [
        (0, 6),
        (6, 7),
        (8, 14),
        (14, 15),
    ]


def test_unsupported_output_has_context_in_strict_mode() -> None:
    g2p = make_g2p(FakeBackend(word_output="r§e"))
    with pytest.raises(RuntimeError, match="Unsupported Hindi Kokoro symbol") as error:
        g2p.lookup("शब्द")
    assert isinstance(error.value.__cause__, HindiVocabularyError)
    assert "शब्द" in str(error.value.__cause__)


def test_lenient_unsupported_word_returns_empty_token_phonemes() -> None:
    tokens = make_g2p(FakeBackend(word_output="r§e"), strict=False)("शब्द")
    assert tokens[0].phonemes is None
    assert tokens[0].rating is None


def test_empty_output_fails_in_strict_mode() -> None:
    with pytest.raises(RuntimeError, match="empty output"):
        make_g2p(FakeBackend(word_output="")).lookup("शब्द")


def test_unknown_options_and_versions_are_rejected() -> None:
    with pytest.raises(TypeError, match="Unsupported HindiG2P options"):
        HindiG2P(custom=True)
    with pytest.raises(ValueError, match="version '1.0'"):
        HindiG2P(version="2.0")
    with pytest.raises(ValueError, match="Unsupported Hindi language"):
        HindiG2P(language="en")


def test_use_cli_is_forwarded_to_lazy_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class RecordingBackend(FakeBackend):
        def __init__(self, **kwargs: object) -> None:
            super().__init__()
            seen.update(kwargs)

    import kokorog2p.backends.espeak as espeak_package

    monkeypatch.setattr(espeak_package, "EspeakBackend", RecordingBackend)
    g2p = HindiG2P(use_cli=True)
    assert g2p._espeak_backend is None
    assert g2p.espeak_backend is not None
    assert seen == {"language": "hi", "with_stress": True, "use_cli": True}
