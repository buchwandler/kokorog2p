from __future__ import annotations

import os

import pytest
from lexphon import DataStore

from benchmarks.station_corpora import LANGUAGES
from kokorog2p import clear_cache, get_g2p
from kokorog2p.lexicons.lexphon_backend import LexphonBackend


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("KOKOROG2P_EXTERNAL_LEXPHON_DATA"),
    reason="released Lexphon data is not provisioned",
)
def test_released_lexhint_assets_are_usable() -> None:
    store = DataStore()
    for language in ("ru-ru", "th-th", "vi-vn", "ja-jp", "ko-kr", "pt-br", "pt-pt"):
        backend = LexphonBackend(language, ("lexhint",), store=store)
        try:
            assert len(backend) > 0, language
        finally:
            backend.close()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("KOKOROG2P_EXTERNAL_LEXPHON_DATA"),
    reason="released Lexphon data is not provisioned",
)
def test_released_german_gold_exposes_clean_pronunciation_and_markers() -> None:
    g2p = get_g2p(
        "de",
        lexicons=("gold",),
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    try:
        for word in ("downloaden", "cancel", "download"):
            evidence = g2p.lexicon_evidence(word)
            assert evidence is not None
            assert evidence.lexicon_id == "de-de:gold"
            assert evidence.rating == 4
            assert evidence.pronunciation is not None
            assert "(en)" not in evidence.pronunciation
            assert "(de)" not in evidence.pronunciation
            markers = evidence.metadata["pronunciation_language_markers"]
            assert markers and markers[0]["language"] == "en"
            rendered = g2p.lookup(word)
            assert rendered is not None
            assert not rendered.startswith("en")
            assert not rendered.endswith("de")
            assert "(en)" not in rendered
            assert "(de)" not in rendered
    finally:
        g2p.close()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("KOKOROG2P_EXTERNAL_LEXPHON_DATA"),
    reason="released Lexphon data is not provisioned",
)
@pytest.mark.parametrize("language", ["ru", "th", "vi"])
def test_released_lexhint_covers_station_smoke_corpus(language: str) -> None:
    clear_cache()
    g2p = get_g2p(
        language,
        use_spacy=False,
        use_espeak_fallback=True,
        use_goruut_fallback=False,
        strict=True,
    )

    for sentence in LANGUAGES[language]["sentences"]:
        tokens = g2p(sentence)
        assert tokens, (language, sentence)
        word_tokens = [
            token for token in tokens if any(char.isalnum() for char in token.text)
        ]
        assert all(token.phonemes for token in word_tokens), (
            language,
            sentence,
            [token.text for token in word_tokens if not token.phonemes],
        )
