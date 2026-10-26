"""Focused English contextual heteronym and provenance regressions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from kokorog2p import TokenAnnotation, phonemize_prepared
from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.en.heteronyms import resolve_english_heteronym
from kokorog2p.en.phoneme_codec import ipa_to_kokoro
from kokorog2p.en.realization import finalize_english_phonemes

_FIXTURE = Path(__file__).parent / "fixtures" / "english_heteronyms.json"
_CASES = json.loads(_FIXTURE.read_text(encoding="utf-8"))["cases"]
_CONTEXT_CASES = [case for case in _CASES if case["classification"] != "exact-tag"]
_WORD_RE = re.compile(r"[\w]+(?:['’][\w]+)*", re.UNICODE)


def _context_windows(case: dict[str, object]) -> tuple[list[str], list[str]]:
    context = str(case["context"])
    word = str(case["word"]).casefold()
    occurrence = int(case.get("occurrence", 1)) - 1
    words = [match.group(0) for match in _WORD_RE.finditer(context)]
    indices = [index for index, token in enumerate(words) if token.casefold() == word]
    index = indices[occurrence]
    return words[max(0, index - 6) : index], words[index + 1 : index + 7]


@pytest.mark.parametrize("case", _CONTEXT_CASES, ids=lambda case: str(case["id"]))
def test_context_resolver_covers_fixture_cases(case: dict[str, object]) -> None:
    left, right = _context_windows(case)
    decision = resolve_english_heteronym(
        str(case["word"]),
        tag=case.get("expected_tag"),
        left_context=left,
        right_context=right,
        sentence_context=str(case["context"]),
    )

    assert decision is not None
    assert decision.ipa == case["expected_ipa"]
    assert decision.reason
    assert decision.context_rule
    assert decision.tag == case.get("expected_tag")
    diagnostic = decision.as_dict()
    assert diagnostic["source"] == "english-context-resolver"
    assert diagnostic["context"]


@pytest.mark.parametrize("case", _CONTEXT_CASES, ids=lambda case: str(case["id"]))
def test_english_g2p_applies_and_traces_contextual_readings(
    case: dict[str, object],
) -> None:
    g2p = EnglishG2P(
        use_espeak_fallback=False,
        use_spacy=False,
        lexicons=(),
        g2lex_files=(),
    )
    try:
        tokens = g2p(str(case["context"]))
        occurrences = [
            token for token in tokens if token.text.casefold() == str(case["word"])
        ]
        token = occurrences[int(case.get("occurrence", 1)) - 1]
        expected = finalize_english_phonemes(
            ipa_to_kokoro(str(case["expected_ipa"])), profile=g2p.frontend_profile
        )

        assert token.phonemes == expected
        diagnostic = token.get("heteronym_resolution")
        assert diagnostic["reason"]
        assert diagnostic["context_rule"]
        assert token.get("pronunciation_source") == "contextual-heteronym"
    finally:
        g2p.close()


@pytest.mark.parametrize("case", _CONTEXT_CASES, ids=lambda case: str(case["id"]))
def test_prepared_context_overrides_misleading_annotations(
    case: dict[str, object],
) -> None:
    context = str(case["context"])
    word = str(case["word"])
    occurrences = [
        match
        for match in _WORD_RE.finditer(context)
        if match.group(0).casefold() == word
    ]
    span = occurrences[int(case.get("occurrence", 1)) - 1]
    annotation = TokenAnnotation(
        span.start(),
        span.end(),
        span.group(0),
        pos="NOUN",
        tag=str(case.get("expected_tag", "NN")),
        lemma=word,
        morph="Number=Sing",
    )
    g2p = EnglishG2P(
        use_espeak_fallback=False,
        use_spacy=False,
        lexicons=(),
        g2lex_files=(),
    )
    try:
        result = phonemize_prepared(
            context,
            language="en-us",
            annotations=[annotation],
            g2p=g2p,
            return_ids=False,
            use_spacy=False,
        )
        token = next(
            item
            for item in result.tokens
            if item.char_start == span.start() and item.text.casefold() == word
        )
        expected = finalize_english_phonemes(
            ipa_to_kokoro(str(case["expected_ipa"])), profile=g2p.frontend_profile
        )

        assert token.meta["phonemes"] == expected
        assert token.meta["heteronym_resolution"]["context_rule"]
        assert token.meta["pronunciation_source"] == "contextual-heteronym"
    finally:
        g2p.close()


def test_pos_alone_does_not_trigger_a_heteronym_decision() -> None:
    assert resolve_english_heteronym("minute", pos="NOUN", tag="NN") is None
    assert resolve_english_heteronym("does", pos="VERB", tag="VBZ") is None


def test_local_file_hit_precedes_contextual_inference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    g2p = EnglishG2P(
        use_espeak_fallback=False,
        use_spacy=False,
        lexicons=(),
        g2lex_files=(),
    )
    try:
        monkeypatch.setattr(
            g2p.lexicon,
            "lookup_hit",
            lambda _word: SimpleNamespace(source_kind="file", lexicon_id="local:test"),
        )
        assert (
            g2p.lookup_contextual("minute", left_context=["a"], right_context=["later"])
            is None
        )
    finally:
        g2p.close()


def test_contextual_resolution_can_be_disabled() -> None:
    g2p = EnglishG2P(
        use_espeak_fallback=False,
        use_spacy=False,
        lexicons=(),
        g2lex_files=(),
        resolve_heteronyms=False,
    )
    try:
        assert (
            g2p.lookup_contextual("minute", left_context=["a"], right_context=["later"])
            is None
        )
    finally:
        g2p.close()
