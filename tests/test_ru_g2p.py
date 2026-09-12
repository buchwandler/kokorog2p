from __future__ import annotations

import pytest
from lexphon import PronunciationToken, PronunciationVariant

from kokorog2p.ru import RussianG2P


class FakeLexphon:
    def __init__(self, pronunciation: str = "ˈslovo") -> None:
        self.pronunciation = pronunciation
        self.closed = False

    def lookup(self, word: str, tag: str | None = None) -> PronunciationToken:
        return PronunciationToken(
            text=word,
            source="lexicon",
            lexicon_id="ru:lexhint",
            matched_key=word,
            source_encoding="ipa",
            variants=(
                PronunciationVariant(
                    pronunciation=self.pronunciation,
                    source_pronunciation=self.pronunciation,
                ),
            ),
        )

    def close(self) -> None:
        self.closed = True

    def lexicon_evidence(self, word: str, tag: str | None = None):
        return None


def _g2p(**kwargs: object) -> RussianG2P:
    g2p = RussianG2P(**kwargs)
    g2p._lexphon = FakeLexphon()  # type: ignore[assignment]
    return g2p


@pytest.mark.parametrize(
    ("use_espeak_fallback", "use_goruut_fallback", "expected"),
    [
        (True, False, "espeak"),
        (False, True, "goruut"),
        (False, False, None),
    ],
)
def test_russian_constructor_configures_fallback(
    monkeypatch: pytest.MonkeyPatch,
    use_espeak_fallback: bool,
    use_goruut_fallback: bool,
    expected: str | None,
) -> None:
    created: list[str | None] = []

    class CapturingBackend:
        def __init__(
            self,
            language: str,
            names: tuple[str, ...] = (),
            *,
            fallback_provider: str | None = None,
            store: object | None = None,
        ) -> None:
            del language, names, store
            created.append(fallback_provider)

        def close(self) -> None:
            return

    monkeypatch.setattr("kokorog2p.ru.g2p.LexphonBackend", CapturingBackend)
    g2p = RussianG2P(
        lexicons=(),
        use_espeak_fallback=use_espeak_fallback,
        use_goruut_fallback=use_goruut_fallback,
    )

    assert g2p.fallback_provider == expected
    assert created == ([] if expected is None else [expected])


def test_russian_factory_forwards_fallback_controls() -> None:
    from kokorog2p import clear_cache, get_g2p

    for options, expected in (
        ({"use_espeak_fallback": True, "use_goruut_fallback": False}, "espeak"),
        ({"use_espeak_fallback": False, "use_goruut_fallback": True}, "goruut"),
        ({"use_espeak_fallback": False, "use_goruut_fallback": False}, None),
    ):
        clear_cache(deep=True)
        g2p = get_g2p("ru", lexicons=(), **options)
        assert g2p.fallback_provider == expected


class ProviderLexphon(FakeLexphon):
    def lookup(self, word: str, tag: str | None = None) -> PronunciationToken:
        del tag
        return PronunciationToken(
            text=word,
            source="provider",
            provider="espeak",
            requested_language="ru",
            variants=(
                PronunciationVariant(
                    pronunciation="lɐˈkɑlʲnəjə",
                    source_pronunciation="lɐˈkɑlʲnəjə",
                ),
            ),
        )


def test_russian_provider_provenance_rating_and_evidence() -> None:
    g2p = _g2p()
    g2p._lexphon = ProviderLexphon()  # type: ignore[assignment]

    token = g2p("локальная")[0]

    assert token.phonemes
    assert token.get("source") == "provider"
    assert token.get("pronunciation_source") == "provider"
    assert token.get("pronunciation_provider") == "espeak"
    assert token.get("pronunciation_requested_language") == "ru"
    assert token.get("pronunciation_source_ipa") == "lɐˈkɑlʲnəjə"
    assert token.get("lexicon_id") is None
    assert token.get("rating") == 1
    assert g2p.lexicon_evidence("локальная") is None


def test_russian_lexhint_provenance_and_offsets() -> None:
    g2p = _g2p()
    tokens = g2p("слово!")
    assert [token.text for token in tokens] == ["слово", "!"]
    assert tokens[0].phonemes == "ˈslovo"
    assert tokens[0].get("source_kind") == "RUSSIAN_WORD"
    assert tokens[0].get("source") == "lexicon"
    assert tokens[0].get("lexicon_id") == "ru:lexhint"
    assert tokens[0].get("rating") == 5
    assert (tokens[0].get("char_start"), tokens[0].get("char_end")) == (0, 5)


def test_preserve_stress_controls_dictionary_stress() -> None:
    assert _g2p(preserve_stress=True)._word_analysis("слово").phonemes == "ˈslovo"
    assert _g2p(preserve_stress=False)._word_analysis("слово").phonemes == "slovo"


def test_russian_lookup_key_is_casefolded() -> None:
    class CapturingLexphon(FakeLexphon):
        def __init__(self) -> None:
            super().__init__()
            self.lookups: list[str] = []

        def lookup(self, word: str, tag: str | None = None):
            self.lookups.append(word)
            return super().lookup(word, tag)

    g2p = RussianG2P()
    backend = CapturingLexphon()
    g2p._lexphon = backend  # type: ignore[assignment]

    analysis = g2p._word_analysis("Быстрая")

    assert analysis.phonemes
    assert backend.lookups == ["быстрая"]


def test_unknown_words_are_strict_or_unresolved() -> None:
    class UnknownLexphon(FakeLexphon):
        def lookup(self, word: str, tag: str | None = None):
            return PronunciationToken(word, "lexicon")

    strict = RussianG2P(use_espeak_fallback=False, use_goruut_fallback=False)
    strict._lexphon = UnknownLexphon()  # type: ignore[assignment]
    with pytest.raises(ValueError, match="ru:lexhint"):
        strict("неслово")

    relaxed = RussianG2P(
        strict=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    relaxed._lexphon = UnknownLexphon()  # type: ignore[assignment]
    assert relaxed("неслово")[0].phonemes is None
    assert relaxed.warnings


def test_latin_policy_and_no_hidden_espeak() -> None:
    preserved = _g2p(latin_policy="preserve")("hello")
    assert preserved[0].get("source_kind") == "LATIN_PRESERVED"
    dropped = _g2p(latin_policy="drop")("hello")
    assert dropped[0].get("source_kind") == "LATIN_DROPPED"
    assert dropped[0].get("drop") is True


def test_russian_word_analysis_accepts_lexhint_tied_affricate():
    g2p = _g2p()
    g2p._lexphon = FakeLexphon("t͡ɕɪˈtɨrʲɪ")

    analysis = g2p._word_analysis("четыре")

    assert analysis.phonemes == "ʨɪˈtɪrʲɪ"
    assert analysis.invalid_symbols == ()


def test_russian_four_token_keeps_source_metadata_after_affricate_normalization():
    g2p = _g2p()
    g2p._lexphon = FakeLexphon("t͡ɕɪˈtɨrʲɪ")

    token = g2p("четыре")[0]

    assert token.text == "четыре"
    assert token.phonemes == "ʨɪˈtɪrʲɪ"
    assert token.get("source_kind") == "RUSSIAN_WORD"
    assert token.get("source") == "lexicon"
    assert token.get("lexicon_id") == "ru:lexhint"
