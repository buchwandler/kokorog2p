"""Phase 1 German spokenform delegation and provenance checks."""

import json
from pathlib import Path

import pytest

from kokorog2p import get_g2p, phonemize
import kokorog2p.pipeline_api as pipeline_api
from kokorog2p.de.g2p import GermanG2P
from kokorog2p.de.normalizer import GermanNormalizer
from kokorog2p.es.g2p import SpanishG2P
from kokorog2p.es.normalizer import SpanishNormalizer
from kokorog2p.fr.g2p import FrenchG2P
from kokorog2p.fr.normalizer import FrenchNormalizer
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
FRENCH_PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "fr_spokenform_parity.json").read_text()
)
SPANISH_PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "es_spokenform_parity.json").read_text()
)


@pytest.mark.parametrize(
    "case",
    FRENCH_PARITY_CASES,
    ids=lambda case: case["category"] + ":" + case["source"][:18],
)
def test_french_parity_corpus(case):
    assert FrenchNormalizer()(case["source"]) == case["expected"]


@pytest.mark.parametrize(
    "case",
    PARITY_CASES,
    ids=lambda case: case["category"] + ":" + case["source"][:18],
)
def test_german_parity_corpus(case):
    assert GermanNormalizer()(case["source"]) == case["expected"]


@pytest.mark.parametrize(
    "case",
    SPANISH_PARITY_CASES,
    ids=lambda case: case["category"] + ":" + case["source"][:18],
)
def test_spanish_parity_corpus(case):
    assert SpanishNormalizer()(case["source"]) == case["expected"]


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
        for left, right in zip(replacements[:-1], replacements[1:], strict=True)
    )
    assert replacements[0].text == "eins Komma fünf Kilogramm"
    assert replacements[1].text == "zwölf Euro achtzig Cent"


def test_spokenform_adapter_handles_empty_and_protected_ranges():
    assert _spokenform_replacements_for_run("plain text", "de") == []
    assert (
        _spokenform_replacements_for_run("1,5 kg", "de", protected_spans=((0, 6),))
        == []
    )


def test_french_adapter_rebases_repeated_source_fragments():
    source = "A 1,5 kg puis 1,5 kg"
    replacements = _spokenform_replacements_for_run(source, "fr", source_offset=10)

    assert [(item.start, item.end) for item in replacements] == [
        (12, 18),
        (24, 30),
    ]
    assert [source[item.start - 10 : item.end - 10] for item in replacements] == [
        "1,5 kg",
        "1,5 kg",
    ]
    assert [item.text for item in replacements] == [
        "un virgule cinq kilogrammes",
        "un virgule cinq kilogrammes",
    ]


def test_french_protection_fails_closed_for_partial_structured_spans():
    replacements = _spokenform_replacements_for_run(
        "5€ 14h30", "fr", protected_spans=((0, 1),)
    )
    assert [(item.start, item.end, item.text) for item in replacements] == [
        (3, 8, "quatorze heures trente")
    ]


def test_spanish_adapter_rebases_repeated_source_fragments():
    source = "A 1 kg y 1 kg"
    replacements = _spokenform_replacements_for_run(source, "es", source_offset=10)

    assert [(item.start, item.end) for item in replacements] == [(12, 16), (19, 23)]
    assert [source[item.start - 10 : item.end - 10] for item in replacements] == [
        "1 kg",
        "1 kg",
    ]
    assert [item.text for item in replacements] == ["un kilogramo", "un kilogramo"]
    assert all(
        left.end <= right.start
        for left, right in zip(replacements[:-1], replacements[1:], strict=True)
    )


def test_spanish_protection_allows_adjacent_semantics():
    source = "25°C y 2 kg"
    replacements = _spokenform_replacements_for_run(
        source,
        "es",
        protected_spans=((0, 4),),
    )

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (7, 11, "dos kilogramos")
    ]


def test_spanish_runs_are_isolated_from_other_languages():
    source = "2 kg and 3 kg"
    tokens = tokenize_with_offsets(source, lang="es", keep_punct=True)
    for token in tokens:
        if token.char_start >= 8:
            token.lang = "en-us"

    replaced, warnings = _apply_structured_replacements_to_tokens(tokens, source, "es")

    assert not warnings
    assert replaced[0].extended_text == "dos kilogramos"
    assert any(token.text == "3" and token.extended_text is None for token in replaced)


@pytest.mark.parametrize("track_changes", [False, True])
def test_spanish_normalizer_direct_api_and_tracking(track_changes):
    normalizer = SpanishNormalizer(track_changes=track_changes)
    normalized, steps = normalizer.normalize("Dr. Pérez tiene 2 kg y 25°C.")

    assert normalized == "Doctor Pérez tiene dos kilogramos y veinticinco grados Celsius."
    if track_changes:
        semantic_rules = [step.rule_name for step in steps]
        assert "es.quantity" in semantic_rules
        assert any(rule.startswith("abbr:") for rule in semantic_rules)
        assert semantic_rules.count("es.quantity") == 2
    else:
        assert steps == []


def test_spanish_token_normalization_is_typography_only():
    normalizer = SpanishNormalizer()

    assert normalizer.normalize_token("2") == "2"
    assert normalizer.normalize_token("Dr.") == "Dr."
    assert normalizer.normalize_token("\u2019") == "'"


@pytest.mark.parametrize("dialect", ["es", "la"])
def test_spanish_direct_and_span_paths_have_phoneme_parity(dialect):
    source = "El Dr. Pérez tiene 2 kg y 25°C."
    g2p = SpanishG2P(
        dialect=dialect,
        use_spacy=False,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
    )
    direct = g2p(source)
    direct_phonemes = "".join(
        (token.phonemes or "") + (token.whitespace or "") for token in direct
    ).strip()
    result = phonemize_to_result(source, lang="es", g2p=g2p, return_ids=False)

    assert result.extended_text == SpanishNormalizer()(source)
    assert result.phonemes == direct_phonemes
    assert not result.warnings


@pytest.mark.parametrize(
    "source, expected",
    [
        ("¿Hola?", "¿Hola?"),
        ("¡Buenos días!", "¡Buenos días!"),
        ("«Hola»", "“Hola”"),
        ("Wait…", "Wait…"),
        ("word — word", "word — word"),
        ("word – word", "word — word"),
    ],
)
def test_spanish_typography_regressions(source, expected):
    assert SpanishNormalizer()(source) == expected


@pytest.mark.parametrize("alias", ["es", "es-es", "spa", "spanish"])
def test_spanish_public_factory_aliases(alias):
    g2p = get_g2p(
        alias,
        use_spacy=False,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
    )
    assert isinstance(g2p, SpanishG2P)
    result = phonemize("Hola 2 kg.", language=alias, return_ids=False)
    assert result.phonemes
    assert not result.warnings


def test_french_runs_are_isolated_from_other_languages():
    source = "1,5 kg 2 kg"
    tokens = tokenize_with_offsets(source, lang="fr", keep_punct=True)
    for token in tokens:
        if token.char_start >= 7:
            token.lang = "en-us"

    replaced, warnings = _apply_structured_replacements_to_tokens(tokens, source, "fr")

    assert not warnings
    assert replaced[0].extended_text == "un virgule cinq kilogrammes"
    assert any(token.text == "2" and token.extended_text is None for token in replaced)


@pytest.mark.parametrize("track_changes", [False, True])
def test_french_normalizer_direct_api_and_tracking(track_changes):
    normalizer = FrenchNormalizer(track_changes=track_changes)
    normalized, steps = normalizer.normalize("Mme Dupont a 1,5 kg.")

    assert normalized == "madame Dupont a un virgule cinq kilogrammes."
    if track_changes:
        assert any(step.rule_name == "fr.quantity" for step in steps)
    else:
        assert steps == []


@pytest.mark.parametrize(
    "expand_nums, expected",
    [
        (True, "trois pommes, quatorze heures trente."),
        (False, "3 pommes, 14h30."),
    ],
)
def test_french_expand_nums_compatibility(expand_nums, expected):
    g2p = FrenchG2P(
        use_spacy=False,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
        expand_nums=expand_nums,
    )
    assert g2p._preprocess("3 pommes, 14h30.") == expected
    assert g2p._normalizer.expand_nums is expand_nums


def test_french_direct_and_span_paths_have_phoneme_parity():
    source = "14h30 et 37°C, puis 1€."
    g2p = FrenchG2P(
        use_spacy=False,
        use_espeak_fallback=False,
        load_gold=False,
        load_silver=False,
    )
    direct = g2p(source)
    direct_phonemes = "".join(
        (token.phonemes or "") + (token.whitespace or "") for token in direct
    ).strip()
    result = phonemize_to_result(source, lang="fr", g2p=g2p, return_ids=False)

    assert result.extended_text == FrenchNormalizer()(source)
    assert result.phonemes == direct_phonemes
    assert not result.warnings


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
