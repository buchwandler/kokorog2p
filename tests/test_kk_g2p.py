"""Unit tests for the Kazakh eSpeak frontend."""

from dataclasses import dataclass

import pytest

from kokorog2p.kk import KazakhG2P
from kokorog2p.kk.model_profile import KazakhVocabularyError


@dataclass
class FakeBackend:
    word_output: str = "rxeqʁ"
    text_output: str = "rxeqʁ rxeqʁ"

    def __post_init__(self) -> None:
        self.word_calls: list[tuple[str, bool]] = []
        self.text_calls: list[tuple[str, bool]] = []

    def word_phonemes(self, word: str, convert_to_kokoro: bool = True) -> str:
        self.word_calls.append((word, convert_to_kokoro))
        return self.word_output

    def phonemize(self, text: str, convert_to_kokoro: bool = True) -> str:
        self.text_calls.append((text, convert_to_kokoro))
        return self.text_output


def make_g2p(backend: FakeBackend, *, strict: bool = True) -> KazakhG2P:
    g2p = KazakhG2P(strict=strict)
    g2p._espeak_backend = backend
    return g2p


def test_aliases_and_metadata() -> None:
    g2p = KazakhG2P(language="kazakh")
    assert g2p.language == "kk"
    assert g2p.get_target_model() == "1.0"
    assert g2p.capabilities()["engine"] == "espeak-ng"
    assert g2p.capabilities()["raw_ipa"] is True


def test_word_processing_requests_raw_ipa() -> None:
    backend = FakeBackend()
    g2p = make_g2p(backend)

    assert g2p.lookup("fixture") == "rxeqʁ"
    assert backend.word_calls == [("fixture", False)]


def test_raw_symbols_are_not_english_converted() -> None:
    assert (
        make_g2p(FakeBackend(word_output="r x e q ʁ")).lookup("fixture") == "r x e q ʁ"
    )


def test_tokens_preserve_punctuation_whitespace_and_offsets() -> None:
    g2p = make_g2p(FakeBackend())
    text = "Сәлем, әлем!"
    tokens = g2p(text)

    assert [(token.text, token.whitespace) for token in tokens] == [
        ("Сәлем", ""),
        (",", " "),
        ("әлем", ""),
        ("!", ""),
    ]
    assert [(token.get("char_start"), token.get("char_end")) for token in tokens] == [
        (0, 5),
        (5, 6),
        (7, 11),
        (11, 12),
    ]
    assert tokens[0].rating == "espeak"
    assert tokens[1].phonemes == ","


def test_text_processing_uses_raw_ipa() -> None:
    backend = FakeBackend()
    assert make_g2p(backend).phonemize("сәлем әлем") == "rxeqʁ rxeqʁ"
    assert backend.text_calls == [("сәлем әлем", False)]


def test_unsupported_output_has_context_in_strict_mode() -> None:
    g2p = make_g2p(FakeBackend(word_output="r§e"))
    with pytest.raises(RuntimeError, match="Unsupported Kazakh Kokoro symbol") as error:
        g2p.lookup("сөз")
    assert isinstance(error.value.__cause__, KazakhVocabularyError)
    assert "сөз" in str(error.value.__cause__)


def test_lenient_unsupported_word_returns_empty_token_phonemes() -> None:
    tokens = make_g2p(FakeBackend(word_output="r§e"), strict=False)("сөз")
    assert tokens[0].phonemes is None
    assert tokens[0].rating is None


def test_empty_output_fails_in_strict_mode() -> None:
    with pytest.raises(RuntimeError, match="empty output"):
        make_g2p(FakeBackend(word_output="")).lookup("сөз")


def test_use_cli_is_forwarded_to_lazy_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    class RecordingBackend(FakeBackend):
        def __init__(self, **kwargs: object) -> None:
            super().__init__()
            seen.update(kwargs)

    import kokorog2p.backends.espeak as espeak_package

    monkeypatch.setattr(espeak_package, "EspeakBackend", RecordingBackend)
    g2p = KazakhG2P(use_cli=True)
    assert g2p.espeak_backend is not None
    assert seen == {"language": "kk", "with_stress": True, "use_cli": True}
