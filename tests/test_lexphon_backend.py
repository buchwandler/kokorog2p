from __future__ import annotations

from pathlib import Path

import pytest
from lexphon import (
    DataStore,
    LexiconNotInstalledError,
    PronunciationLanguageMarker,
    PronunciationToken,
    PronunciationVariant,
)

import kokorog2p.lexicons.lexphon_backend as backend_module
from kokorog2p.lexicons.lexphon_backend import LexphonBackend


class _FakePhonemizer:
    def __init__(self) -> None:
        self.closed = False
        self.layers = ()
        self.lexicon_calls: list[tuple[str, str | None]] = []
        self.lookup_calls: list[tuple[str, str | None]] = []
        self.many_calls: list[tuple[tuple[str, ...], str | None]] = []

    def lookup_lexicon(self, word: str, *, tag: str | None = None):
        self.lexicon_calls.append((word, tag))

    def lookup(self, word: str, *, tag: str | None = None):
        self.lookup_calls.append((word, tag))
        return (word, tag)

    def lookup_many(self, words, *, tag: str | None = None):
        words = tuple(words)
        self.many_calls.append((words, tag))
        return tuple((word, tag) for word in words)

    def lookup_prefixes(self, text: str, *, position: int = 0, tag: str | None = None):
        return ((text[position:], tag),)

    def close(self) -> None:
        self.closed = True


def test_backend_keeps_phonemizer_lazy() -> None:
    fake = _FakePhonemizer()
    backend = LexphonBackend("ru-ru", ("lexhint",), phonemizer=fake)  # type: ignore[arg-type]
    assert backend.ids == ("ru:lexhint",)
    assert backend.lookup("слово") == ("слово", None)
    assert backend.lookup_prefixes("слово", position=1) == (("лово", None),)
    backend.close()
    assert fake.closed


def test_backend_distinguishes_lexical_and_full_lookup() -> None:
    fake = _FakePhonemizer()
    backend = LexphonBackend("ru-ru", ("lexhint",), phonemizer=fake)  # type: ignore[arg-type]
    try:
        assert backend.lookup_lexicon_token("слово") is None
        assert backend.lookup_token("слово") == ("слово", None)
        assert fake.lexicon_calls == [("слово", None)]
        assert fake.lookup_calls == [("слово", None)]
        assert backend.lexicon_evidence("слово") is None
        assert fake.lexicon_calls == [("слово", None), ("слово", None)]
    finally:
        backend.close()


def test_backend_uses_one_batch_call() -> None:
    fake = _FakePhonemizer()
    backend = LexphonBackend("ru-ru", ("lexhint",), phonemizer=fake)  # type: ignore[arg-type]
    try:
        assert backend.lookup_many(("eins", "zwei"), tag="NOUN") == (
            ("eins", "NOUN"),
            ("zwei", "NOUN"),
        )
        assert fake.many_calls == [(("eins", "zwei"), "NOUN")]
    finally:
        backend.close()


def test_provider_only_backend_passes_empty_lexicons(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created: dict[str, object] = {}

    class ConstructedFake(_FakePhonemizer):
        def __init__(self, language: str, **kwargs: object) -> None:
            super().__init__()
            created["language"] = language
            created.update(kwargs)

    monkeypatch.setattr(backend_module, "Phonemizer", ConstructedFake)
    backend = LexphonBackend("en-us", fallback_provider="espeak")
    try:
        backend.lookup_token("File")
        assert created["language"] == "en-us"
        assert created["lexicons"] == []
        assert created["fallback"] == "espeak"
    finally:
        backend.close()


def test_swedish_backend_resolves_registry_external_id() -> None:
    backend = LexphonBackend(
        "sv-se",
        ("nst",),
        phonemizer=_FakePhonemizer(),  # type: ignore[arg-type]
    )
    try:
        assert backend.ids == ("sv-se:nst",)
    finally:
        backend.close()


def test_provider_token_does_not_become_lexicon_evidence() -> None:
    provider_token = PronunciationToken(
        text="File",
        source="provider",
        provider="espeak",
        requested_language="de-de",
    )

    class ProviderFake(_FakePhonemizer):
        def lookup(self, word: str, *, tag: str | None = None):
            return provider_token

    backend = LexphonBackend(
        "de-de",
        phonemizer=ProviderFake(),  # type: ignore[arg-type]
    )
    try:
        assert backend.lookup_token("File") is provider_token
        assert backend.lexicon_evidence("File") is None
    finally:
        backend.close()

def test_provider_metadata_serializes_structured_source() -> None:
    from kokorog2p.lexicons.lexphon_backend import provider_metadata

    token = PronunciationToken(
        text="File",
        source="provider",
        provider="espeak",
        requested_language="de-de",
        variants=(
            PronunciationVariant(
                pronunciation="fˈIl",
                source_pronunciation="(en)fˈIl(de)",
                language_markers=(
                    PronunciationLanguageMarker("en", 0),
                    PronunciationLanguageMarker("de", 4),
                ),
            ),
        ),
    )

    assert provider_metadata(token) == {
        "pronunciation_source": "provider",
        "pronunciation_provider": "espeak",
        "pronunciation_requested_language": "de-de",
        "pronunciation_source_ipa": "(en)fˈIl(de)",
        "pronunciation_language_markers": [
            {"language": "en", "ipa_offset": 0},
            {"language": "de", "ipa_offset": 4},
        ],
    }



def test_backend_does_not_open_missing_data_until_lookup(tmp_path: Path) -> None:
    backend = LexphonBackend("th-th", ("lexhint",), store=DataStore(tmp_path / "store"))
    try:
        with pytest.raises(LexiconNotInstalledError) as error:
            backend.lookup("ไทย")
        message = str(error.value)
        assert "th:lexhint" in message
        assert "lexphon data install th:lexhint" in message
        assert "lexphon data verify th:lexhint" in message
    finally:
        backend.close()
