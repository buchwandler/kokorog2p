"""Focused contracts for the runnable advanced examples."""

from __future__ import annotations

import os
import shutil

import pytest

from kokorog2p import (
    GToken,
    OverrideSpan,
    TokenAnnotation,
    available_lexicons,
    cache_info,
    clear_cache,
    get_g2p,
    ids_to_phonemes,
    lexicon_info,
    phonemize_prepared,
)


def test_result_inspection_contract() -> None:
    source = "Hallo Welt!"
    result = phonemize_prepared(
        source,
        language="de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        return_phonemes=True,
        return_ids=True,
    )

    assert result.phonemes
    assert result.token_ids
    assert ids_to_phonemes(result.token_ids) == result.phonemes
    assert not result.warnings
    for token in result.tokens:
        assert source[token.char_start : token.char_end] == token.text


def test_structured_stress_changes_only_selected_token() -> None:
    source = "Hallo Welt"
    base = phonemize_prepared(
        source,
        language="de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        return_ids=False,
    )
    primary = phonemize_prepared(
        source,
        language="de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        overrides=[OverrideSpan(0, 5, {"stress": "+2"})],
        return_ids=False,
    )
    unstressed = phonemize_prepared(
        source,
        language="de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        overrides=[OverrideSpan(0, 5, {"stress": "-2"})],
        return_ids=False,
    )

    base_words = [token for token in base.tokens if token.text.isalpha()]
    primary_words = [token for token in primary.tokens if token.text.isalpha()]
    unstressed_words = [token for token in unstressed.tokens if token.text.isalpha()]
    assert primary_words[0].meta["phonemes"] != base_words[0].meta["phonemes"]
    assert "ˈ" in primary_words[0].meta["phonemes"]
    assert "ˈ" not in unstressed_words[0].meta["phonemes"]
    assert primary_words[1].meta["phonemes"] == base_words[1].meta["phonemes"]
    assert unstressed_words[1].meta["phonemes"] == base_words[1].meta["phonemes"]


def test_cache_reuses_identity_and_reports_bounded_lru() -> None:
    clear_cache(deep=True)
    first = get_g2p("de", lexicons=(), use_spacy=False, use_espeak_fallback=False)
    second = get_g2p("de", lexicons=(), use_spacy=False, use_espeak_fallback=False)
    distinct = get_g2p(
        "de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        phoneme_quotes="ascii",
    )

    assert first is second
    assert first is not distinct
    info = cache_info()
    assert info.policy == "bounded-lru"
    assert info.size <= info.maxsize


class _AnnotatedG2P:
    """Small injected frontend used to verify parser-free annotation delivery."""

    use_spacy = True
    version = "1.0"

    def __call__(self, text: str) -> list[GToken]:
        assert not self.use_spacy
        token = GToken(text=text, whitespace="", phonemes="base")
        token.set("char_start", 0)
        token.set("char_end", len(text))
        return [token]

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        del word
        return "noun" if tag == "NN" else None


def test_external_annotation_example_contract_without_spacy() -> None:
    result = phonemize_prepared(
        "record",
        language="en-us",
        annotations=[TokenAnnotation(0, 6, "record", pos="NOUN", tag="NN")],
        g2p=_AnnotatedG2P(),
        return_ids=False,
    )

    assert result.phonemes == "noun"
    assert result.tokens[0].meta["tag"] == "NN"


@pytest.mark.espeak
@pytest.mark.skipif(
    not (shutil.which("espeak-ng") or shutil.which("espeak")),
    reason="neither espeak-ng nor espeak is available on PATH",
)
def test_dynamic_espeak_fallback_provenance() -> None:
    clear_cache(deep=True)
    with_fallback = get_g2p(
        "en-us",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=True,
        use_goruut_fallback=False,
    )
    without_fallback = get_g2p(
        "en-us",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )

    token = next(token for token in with_fallback("fallbackdemo") if token.is_word)
    without_token = next(
        token for token in without_fallback("fallbackdemo") if token.is_word
    )
    assert without_token.phonemes == "❓"
    assert token.phonemes
    assert token.get("pronunciation_source") == "provider"
    assert token.get("pronunciation_provider") == "espeak"


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("KOKOROG2P_EXTERNAL_LEXPHON_DATA") != "1",
    reason="set KOKOROG2P_EXTERNAL_LEXPHON_DATA=1 for released Lexphon data",
)
def test_named_crane_lexicon_selection_and_evidence() -> None:
    assert "crane" in available_lexicons("de")
    assert lexicon_info("de", "crane")["id"] == "de-de:crane"

    g2p = get_g2p(
        "de",
        lexicons="crane",
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    evidence = g2p.lexicon_evidence("Haus")
    assert evidence is not None
    assert evidence.lexicon_id == "de-de:crane"
