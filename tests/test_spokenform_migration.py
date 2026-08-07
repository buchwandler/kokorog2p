"""Phase 1 German spokenform delegation and provenance checks."""

import json
from pathlib import Path

import pytest

import kokorog2p.pipeline_api as pipeline_api
from kokorog2p.de.g2p import GermanG2P
from kokorog2p.de.normalizer import GermanNormalizer
from kokorog2p.pipeline_api import (
    _apply_structured_replacements_to_tokens,
    _spokenform_replacements_for_run,
    phonemize_to_result,
)
from kokorog2p.tokenization import tokenize_with_offsets
from kokorog2p.types import OverrideSpan

PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "de_semantic_parity.json").read_text()
)


@pytest.mark.parametrize(
    "case",
    PARITY_CASES,
    ids=lambda case: case["category"] + ":" + case["source"][:18],
)
def test_german_parity_corpus(case):
    assert GermanNormalizer()(case["source"]) == case["expected"]


def test_spokenform_adapter_rebases_and_preserves_source_provenance():
    source = "1,5 kg und 12,80 EUR"
    replacements = _spokenform_replacements_for_run(source, "de", source_offset=10)

    assert [(item.start, item.end) for item in replacements] == [(10, 16), (21, 30)]
    assert [source[item.start - 10 : item.end - 10] for item in replacements] == [
        "1,5 kg",
        "12,80 EUR",
    ]
    assert all(
        left.end <= right.start
        for left, right in zip(replacements, replacements[1:], strict=True)
    )
    assert replacements[0].text == "eins Komma fünf Kilogramm"
    assert replacements[1].text == "zwölf Euro achtzig Cent"


def test_spokenform_adapter_handles_empty_and_protected_ranges():
    assert _spokenform_replacements_for_run("plain text", "de") == []
    assert (
        _spokenform_replacements_for_run("1,5 kg", "de", protected_spans=((0, 6),))
        == []
    )


def test_german_runs_are_prepared_independently(monkeypatch):
    source = "1,5 kg and 2 kg"
    tokens = tokenize_with_offsets(source, lang="de", keep_punct=True)
    for token in tokens:
        if token.char_start >= 11:
            token.lang = "en-us"
            token.lang = "en-us"

    calls = []
    real_adapter = pipeline_api._spokenform_replacements_for_run

    def record_call(text, language, **kwargs):
        calls.append((text, language))
        return real_adapter(text, language, **kwargs)

    monkeypatch.setattr(pipeline_api, "_spokenform_replacements_for_run", record_call)
    replaced, warnings = _apply_structured_replacements_to_tokens(tokens, source, "de")

    assert calls == [("1,5 kg and", "de")]
    assert not warnings
    assert replaced[0].extended_text == "eins Komma fünf Kilogramm"
    assert any(token.text == "2" and token.extended_text is None for token in replaced)


def test_override_protects_quantity_but_allows_adjacent_quantity():
    source = "1,5 kg und 2 kg"
    result = phonemize_to_result(
        source,
        lang="de",
        overrides=[OverrideSpan(0, 6, {"ph": "a"})],
        return_ids=False,
    )

    assert result.extended_text.startswith("1,5 kg und zwei Kilogramm")
    assert result.tokens[0].meta.get("ph") == "a"
    assert not any("[ALIGNMENT]" in warning for warning in result.warnings)


def test_override_protects_number_plus_unit_and_preserves_offsets():
    source = "3°C neben 4°C"
    result = phonemize_to_result(
        source,
        lang="de",
        overrides=[OverrideSpan(0, 3, {"ph": "a"})],
        return_ids=False,
    )

    assert result.extended_text.startswith("3 C neben vier Grad Celsius")
    assert (
        result.clean_text[result.tokens[0].char_start : result.tokens[0].char_end]
        == result.tokens[0].text
    )


def test_representative_direct_and_pipeline_phonemes_match():
    source = "Prof. Klein hat 1,5 kg."
    g2p = GermanG2P(
        use_lexicon=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        load_gold=False,
        load_silver=False,
    )

    direct_tokens = g2p(GermanNormalizer()(source))
    direct_phonemes = "".join(
        (token.phonemes or "") + (token.whitespace or "") for token in direct_tokens
    ).strip()
    result = phonemize_to_result(source, lang="de", g2p=g2p, return_ids=False)

    assert result.phonemes == direct_phonemes
    assert not result.warnings
