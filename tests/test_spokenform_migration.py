"""Spokenform delegation and provenance checks for migrated languages."""

import json
from pathlib import Path

import pytest

import kokorog2p.pipeline_api as pipeline_api
from kokorog2p import get_g2p, phonemize
from kokorog2p.cs.g2p import CzechG2P
from kokorog2p.cs.normalizer import CzechNormalizer
from kokorog2p.de.g2p import GermanG2P
from kokorog2p.de.normalizer import GermanNormalizer
from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.en.normalizer import EnglishNormalizer
from kokorog2p.es.g2p import SpanishG2P
from kokorog2p.es.normalizer import SpanishNormalizer
from kokorog2p.fr.g2p import FrenchG2P
from kokorog2p.fr.normalizer import FrenchNormalizer
from kokorog2p.it.g2p import ItalianG2P
from kokorog2p.it.normalizer import ItalianNormalizer
from kokorog2p.pipeline_api import (
    _apply_structured_replacements_to_tokens,
    _spokenform_replacements_for_run,
    _uses_spokenform_semantics,
    phonemize_to_result,
)
from kokorog2p.pt.g2p import PortugueseG2P
from kokorog2p.pt.normalizer import PortugueseNormalizer
from kokorog2p.tokenization import tokenize_with_offsets
from kokorog2p.types import OverrideSpan


def assert_spokenform_handoff(
    source: str,
    language: str,
    *,
    protected_spans=(),
) -> None:
    """Assert the compact semantic handoff contract at the adapter boundary."""

    from spokenform import PreparationConfig, prepare_for_kokorog2p

    prepared = prepare_for_kokorog2p(
        source,
        language=language,
        config=PreparationConfig.for_kokorog2p(language),
        protected_spans=protected_spans,
    )
    for replacement in prepared.source_replacements:
        assert source[replacement.source_start : replacement.source_end] == replacement.source

    result = phonemize_to_result(source, lang=language, return_ids=False)
    assert result.extended_text == prepared.spoken_text

PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "de_semantic_parity.json").read_text()
)
FRENCH_PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "fr_spokenform_parity.json").read_text()
)
SPANISH_PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "es_spokenform_parity.json").read_text()
)
PORTUGUESE_PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "pt_spokenform_parity.json").read_text()
)
CS_PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "cs_spokenform_parity.json").read_text()
)
ENGLISH_PARITY_CASES = json.loads(
    (Path(__file__).parent / "data" / "en_spokenform_parity.json").read_text()
)


def test_english_aliases_use_the_generic_spokenform_adapter():
    assert all(
        _uses_spokenform_semantics(language) for language in ("en", "en-us", "en-gb")
    )


@pytest.mark.parametrize(
    "case",
    ENGLISH_PARITY_CASES,
    ids=lambda case: case["category"] + ":" + case["source"][:18],
)
def test_english_parity_corpus(case):
    assert EnglishNormalizer()(case["source"]) == case["expected"]


def test_english_dot_zero_version_label_is_prepared_by_spokenform():
    source = "We had built bot 2.0."

    assert EnglishNormalizer()(source) == "We had built bot two point oh."


def test_english_version_label_adapter_rebases_exact_span_and_excludes_period():
    source = "We had built bot 2.0."
    source_offset = 10
    replacements = _spokenform_replacements_for_run(
        source, "en-us", source_offset=source_offset
    )

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (source_offset + 17, source_offset + 20, "two point oh")
    ]
    replacement = replacements[0]
    assert (
        source[replacement.start - source_offset : replacement.end - source_offset]
        == "2.0"
    )
    assert source[replacement.end - source_offset] == "."


def test_english_version_label_public_pipeline_preserves_source_alignment():
    source = "We had built bot 2.0."
    result = phonemize_to_result(source, lang="en-us", return_ids=False)

    assert result.clean_text == source
    assert result.extended_text == "We had built bot two point oh."
    assert result.extended_text.endswith(".")
    assert not any(character.isdigit() for character in result.extended_text)
    assert result.phonemes
    assert not result.warnings
    assert all(
        0 <= token.char_start <= token.char_end <= len(source)
        for token in result.tokens
    )


def test_english_adapter_rebases_repeated_sources_and_preserves_provenance():
    source = "2 kg and 2 kg"
    replacements = _spokenform_replacements_for_run(source, "en", source_offset=10)

    assert [(item.start, item.end) for item in replacements] == [(10, 14), (19, 23)]
    assert [source[item.start - 10 : item.end - 10] for item in replacements] == [
        "2 kg",
        "2 kg",
    ]
    assert [item.text for item in replacements] == ["two kilograms", "two kilograms"]


def test_english_adapter_keeps_terminal_quantity_punctuation_outside_span():
    replacements = _spokenform_replacements_for_run("30C.", "en-us")

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (0, 3, "thirty degrees Celsius")
    ]


def test_english_adapter_protection_fails_closed_but_adjacent_semantics_apply():
    source = "37 C. and 2 kg"
    replacements = _spokenform_replacements_for_run(
        source, "en-us", protected_spans=((0, 5),)
    )

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (10, 14, "two kilograms")
    ]


def test_english_adapter_keeps_abbreviations_adjacent_to_quantities():
    source = "Visit St. and 2 kg"
    replacements = _spokenform_replacements_for_run(source, "en-gb")

    assert [source[item.start : item.end] for item in replacements] == ["St.", "2 kg"]
    assert [item.text for item in replacements] == ["Saint", "two kilograms"]


def test_english_runs_are_isolated_from_other_languages(monkeypatch):
    source = "2 kg and 3 kg"
    tokens = tokenize_with_offsets(source, lang="en-us", keep_punct=True)
    for token in tokens:
        if token.char_start >= 8:
            token.lang = "de"

    calls = []
    real_adapter = pipeline_api._spokenform_replacements_for_run

    def record_call(text, language, **kwargs):
        calls.append((text, language))
        return real_adapter(text, language, **kwargs)

    monkeypatch.setattr(pipeline_api, "_spokenform_replacements_for_run", record_call)
    replaced, warnings = _apply_structured_replacements_to_tokens(
        tokens, source, "en-us"
    )

    assert calls == [("2 kg and", "en-us"), ("3 kg", "de")]
    assert not warnings
    assert replaced[0].extended_text == "two kilograms"
    assert any(
        token.text == "3 kg" and token.extended_text == "drei Kilogramm"
        for token in replaced
    )


def test_english_symbols_survive_top_level_preprocessing():
    source = "$12.50, £2.00, €3.00 and 50%"
    result = phonemize_to_result(source, lang="en-us", return_ids=False)

    assert result.clean_text == source
    assert result.extended_text == (
        "twelve dollars and fifty cents, two pounds, three euros and fifty%"
    )
    assert "$" not in result.extended_text
    assert "£" not in result.extended_text
    assert "€" not in result.extended_text
    assert "fifty%" in result.extended_text


def test_english_direct_and_public_pipeline_have_phoneme_parity():
    source = "Dr. Smith has 2 kg at 3:00."
    g2p = EnglishG2P(
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        load_gold=True,
        load_silver=False,
    )
    direct = g2p(source)
    direct_phonemes = "".join(
        (token.phonemes or "") + (token.whitespace or "") for token in direct
    ).strip()
    result = phonemize_to_result(source, lang="en-us", g2p=g2p, return_ids=False)

    assert result.extended_text == EnglishNormalizer()(source)
    assert result.phonemes == direct_phonemes
    assert not result.warnings


def test_english_preparation_is_idempotent_before_direct_g2p():
    normalizer = EnglishNormalizer()
    prepared = normalizer("At 3:00, pay $12.50 for 2 kg.")

    assert normalizer(prepared) == prepared


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


@pytest.mark.parametrize(
    "case",
    PORTUGUESE_PARITY_CASES,
    ids=lambda case: case["category"] + ":" + case["source"][:18],
)
def test_portuguese_parity_corpus(case):
    assert PortugueseNormalizer()(case["source"]) == case["expected"]


@pytest.mark.parametrize(
    "case",
    CS_PARITY_CASES,
    ids=lambda case: case["category"] + ":" + case["source"][:18],
)
def test_czech_parity_corpus(case):
    assert CzechNormalizer()(case["source"]) == case["expected"]


def test_czech_direct_g2p_speaks_supported_semantics_without_unknowns():
    g2p = CzechG2P(use_espeak_fallback=False, use_goruut_fallback=False)
    tokens = g2p("Dr. Novák má 2 kg a teplota je 25°C.")

    assert all(
        not any(character.isdigit() for character in token.text) for token in tokens
    )
    assert all(token.phonemes not in (None, "?") for token in tokens if token.is_word)
    assert next(token for token in tokens if token.text == "Novák").phonemes == "novaːk"


def test_czech_public_pipeline_prepares_semantics_once_and_preserves_alignment():
    source = "Dr. Novák má 2 kg a teplota je 25°C."
    result = phonemize_to_result(source, lang="cs-cz", return_ids=False)

    assert result.extended_text == (
        "Doktor Novák má dva kilogramy a teplota je dvacet pět stupňů Celsia."
    )
    assert not any(character.isdigit() for character in result.extended_text)
    assert not any(
        token.extended_text and token.extended_text.count("dva") > 1
        for token in result.tokens
    )
    assert result.extended_text.endswith(".")
    assert result.phonemes
    assert not result.warnings
    assert all(
        token.char_start <= token.char_end <= len(source) for token in result.tokens
    )


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


def test_italian_adapter_rebases_repeated_source_fragments():
    source = "A 1,5 kg e 1,5 kg"
    replacements = _spokenform_replacements_for_run(source, "it", source_offset=10)

    assert [(item.start, item.end) for item in replacements] == [
        (12, 18),
        (21, 27),
    ]
    assert [source[item.start - 10 : item.end - 10] for item in replacements] == [
        "1,5 kg",
        "1,5 kg",
    ]
    assert [item.text for item in replacements] == [
        "uno virgola cinque chilogrammi",
        "uno virgola cinque chilogrammi",
    ]
    assert all(
        left.end <= right.start
        for left, right in zip(replacements[:-1], replacements[1:], strict=True)
    )


def test_italian_protection_allows_adjacent_semantics():
    replacements = _spokenform_replacements_for_run(
        "25°C e 2 kg", "it", protected_spans=((0, 4),)
    )

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (7, 11, "due chilogrammi")
    ]


def test_portuguese_adapter_rebases_repeated_source_fragments():
    source = "A 1,5 kg e 1,5 kg"
    replacements = _spokenform_replacements_for_run(source, "pt", source_offset=10)

    assert [(item.start, item.end) for item in replacements] == [
        (12, 18),
        (21, 27),
    ]
    assert [source[item.start - 10 : item.end - 10] for item in replacements] == [
        "1,5 kg",
        "1,5 kg",
    ]
    assert [item.text for item in replacements] == [
        "um vírgula cinco quilogramas",
        "um vírgula cinco quilogramas",
    ]
    assert all(
        left.end <= right.start
        for left, right in zip(replacements[:-1], replacements[1:], strict=True)
    )


@pytest.mark.parametrize("protected_span", [((0, 4),), ((0, 1),)])
def test_portuguese_protection_preserves_intersecting_quantity_and_allows_adjacent(
    protected_span,
):
    replacements = _spokenform_replacements_for_run(
        "25°C e 2 kg",
        "pt",
        protected_spans=protected_span,
    )

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (7, 11, "dois quilogramas")
    ]


def test_portuguese_runs_are_isolated_from_other_languages(monkeypatch):
    source = "2 kg e 3 kg"
    tokens = tokenize_with_offsets(source, lang="pt", keep_punct=True)
    for token in tokens:
        if token.char_start >= 7:
            token.lang = "en-us"

    calls = []
    real_adapter = pipeline_api._spokenform_replacements_for_run

    def record_call(text, language, **kwargs):
        calls.append((text, language))
        return real_adapter(text, language, **kwargs)

    monkeypatch.setattr(pipeline_api, "_spokenform_replacements_for_run", record_call)
    replaced, warnings = _apply_structured_replacements_to_tokens(tokens, source, "pt")

    assert calls == [("2 kg e", "pt"), ("3 kg", "en-us")]
    assert not warnings
    assert replaced[0].extended_text == "dois quilogramas"
    assert any(
        token.text == "3 kg" and token.extended_text == "three kilograms"
        for token in replaced
    )


@pytest.mark.parametrize(
    "dialect, expected", [("br", "dezesseis"), ("pt", "dezasseis")]
)
def test_portuguese_normalizer_routes_dialect_semantics(dialect, expected):
    normalizer = PortugueseNormalizer(dialect=dialect)
    assert normalizer("16") == expected
    assert normalizer("R$ 16,80").endswith(
        "oitenta centavos" if dialect == "br" else "oitenta cêntimos"
    )


def test_portuguese_normalizer_token_api_is_typography_only():
    normalizer = PortugueseNormalizer()

    assert normalizer.normalize_token("16") == "16"
    assert normalizer.normalize_token("Dr.") == "Dr."
    assert normalizer.normalize_token("\u2019") == "'"


def test_portuguese_direct_g2p_accepts_spoken_semantic_forms_and_is_idempotent():
    normalizer = PortugueseNormalizer()
    spoken = "dezesseis quilogramas e oitenta centavos"
    assert normalizer(normalizer(spoken)) == spoken

    g2p = PortugueseG2P(use_spacy=False, use_espeak_fallback=False)
    tokens = g2p("Doutor Ana tem vinte e cinco graus Celsius")
    assert all(token.phonemes not in (None, "?") for token in tokens if token.is_word)


def test_portuguese_full_pipeline_prepares_semantics_before_g2p():
    source = "Dr. Ana tem 1,5 kg, 25°C e paga R$ 12,80 — ok."
    result = phonemize_to_result(source, lang="pt", return_ids=False)

    assert result.extended_text == (
        "Doutor Ana tem um vírgula cinco quilogramas, "
        "vinte e cinco graus Celsius e paga doze reais e oitenta centavos — ok."
    )
    assert not any(character.isdigit() for character in result.extended_text)
    assert "kg" not in result.extended_text
    assert "R$" not in result.extended_text
    assert result.phonemes
    assert not result.warnings


def test_italian_runs_are_isolated_from_other_languages(monkeypatch):
    source = "2 kg and 3 kg"
    tokens = tokenize_with_offsets(source, lang="it", keep_punct=True)
    for token in tokens:
        if token.char_start >= 8:
            token.lang = "en-us"

    calls = []
    real_adapter = pipeline_api._spokenform_replacements_for_run

    def record_call(text, language, **kwargs):
        calls.append((text, language))
        return real_adapter(text, language, **kwargs)

    monkeypatch.setattr(pipeline_api, "_spokenform_replacements_for_run", record_call)
    replaced, warnings = _apply_structured_replacements_to_tokens(tokens, source, "it")

    assert calls == [("2 kg and", "it"), ("3 kg", "en-us")]
    assert not warnings
    assert replaced[0].extended_text == "due chilogrammi"
    assert any(
        token.text == "3 kg" and token.extended_text == "three kilograms"
        for token in replaced
    )


def test_italian_normalizer_direct_api_and_tracking():
    normalizer = ItalianNormalizer(track_changes=True)
    normalized, steps = normalizer.normalize("Prof. Klein ha 1,5 kg e 25°C.")

    assert normalized == (
        "Professor Klein ha uno virgola cinque chilogrammi e venticinque gradi Celsius."
    )
    semantic_rules = [step.rule_name for step in steps]
    assert semantic_rules.count("it.quantity") == 2
    assert "abbr:Prof." in semantic_rules


def test_italian_token_normalization_is_typography_only():
    normalizer = ItalianNormalizer()

    assert normalizer.normalize_token("1,5") == "1,5"
    assert normalizer.normalize_token("Prof.") == "Prof."
    assert normalizer.normalize_token("\u2019") == "'"


def test_italian_override_protects_quantity_and_preserves_coordinates():
    source = "1,5 kg e 2 kg"
    result = phonemize_to_result(
        source,
        lang="it",
        overrides=[OverrideSpan(0, 6, {"ph": "a"})],
        return_ids=False,
    )

    assert result.extended_text == "1,5 kg e due chilogrammi"
    assert result.tokens[0].meta.get("ph") == "a"
    assert result.tokens[0].char_start == 0
    assert result.tokens[0].char_end == 6
    assert "\ue000" not in result.extended_text
    assert not any("[ALIGNMENT]" in warning for warning in result.warnings)


@pytest.mark.parametrize(
    "source, expected",
    [
        ("12,80 EUR", "dodici euro e ottanta centesimi"),
        ("€12,80", "dodici euro e ottanta centesimi"),
        ("25°C", "venticinque gradi Celsius"),
    ],
)
def test_italian_currency_and_temperature_symbols_survive_top_level_preprocessing(
    source, expected
):
    result = phonemize_to_result(source, lang="it", return_ids=False)

    assert result.clean_text == source
    assert result.extended_text == expected
    assert "\ue000" not in result.clean_text
    assert "\ue000" not in result.extended_text


def test_italian_direct_and_span_paths_have_phoneme_parity():
    source = "Prof. Klein usa 25°C, 1,5 kg e 12,80 EUR."
    g2p = ItalianG2P(
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    direct = g2p(source)
    direct_phonemes = "".join(
        (token.phonemes or "") + (token.whitespace or "") for token in direct
    ).strip()
    result = phonemize_to_result(source, lang="it", g2p=g2p, return_ids=False)

    assert result.extended_text == ItalianNormalizer()(source)
    assert result.phonemes == direct_phonemes
    assert not result.warnings


def test_italian_top_level_result_uses_reviewed_semantics():
    source = "Il 14.05.2026 il Prof. Klein usa 1,5 kg e paga 12,80 EUR."
    result = phonemize_to_result(source, lang="it", return_ids=False)

    assert "quattordici maggio duemilaventisei" in result.extended_text
    assert "Professor" in result.extended_text
    assert "uno virgola cinque chilogrammi" in result.extended_text
    assert "dodici euro e ottanta centesimi" in result.extended_text
    assert not any(character.isdigit() for character in result.extended_text)
    assert all(
        0 <= token.char_start <= token.char_end <= len(result.clean_text)
        for token in result.tokens
    )
    assert "\ue000" not in result.extended_text


def test_italian_direct_g2p_accepts_spoken_semantic_forms_and_is_idempotent():
    normalizer = ItalianNormalizer()
    spoken = "dodici euro e ottanta centesimi"
    assert normalizer(normalizer(spoken)) == spoken

    g2p = ItalianG2P(use_spacy=False, use_espeak_fallback=False)
    tokens = g2p("Prof. Klein 25°C 1,5 kg 12,80 EUR")
    assert all(token.phonemes not in (None, "?") for token in tokens if token.is_word)


def test_spanish_runs_are_isolated_from_other_languages():
    source = "2 kg and 3 kg"
    tokens = tokenize_with_offsets(source, lang="es", keep_punct=True)
    for token in tokens:
        if token.char_start >= 8:
            token.lang = "en-us"

    replaced, warnings = _apply_structured_replacements_to_tokens(tokens, source, "es")

    assert not warnings
    assert replaced[0].extended_text == "dos kilogramos"
    assert any(
        token.text == "3 kg" and token.extended_text == "three kilograms"
        for token in replaced
    )


@pytest.mark.parametrize("track_changes", [False, True])
def test_spanish_normalizer_direct_api_and_tracking(track_changes):
    normalizer = SpanishNormalizer(track_changes=track_changes)
    normalized, steps = normalizer.normalize("Dr. Pérez tiene 2 kg y 25°C.")

    assert normalized == (
        "Doctor Pérez tiene dos kilogramos y veinticinco grados Celsius."
    )
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
    assert any(
        token.text == "2 kg" and token.extended_text == "two kilograms"
        for token in replaced
    )


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

    assert calls == [("1,5 kg and", "de"), ("2 kg", "en-us")]
    assert not warnings
    assert replaced[0].extended_text == "eins Komma fünf Kilogramm"
    assert any(
        token.text == "2 kg" and token.extended_text == "two kilograms"
        for token in replaced
    )


def test_german_extended_quantity_replacements_rebase_and_repeat():
    source = "prefix 1 m³ and 2 km/h"
    replacements = _spokenform_replacements_for_run(source, "de", source_offset=10)

    assert [(item.start, item.end) for item in replacements] == [
        (10 + source.index("1 m³"), 10 + source.index("1 m³") + len("1 m³")),
        (10 + source.index("2 km/h"), 10 + source.index("2 km/h") + len("2 km/h")),
    ]
    assert [item.text for item in replacements] == [
        "ein Kubikmeter",
        "zwei Kilometer pro Stunde",
    ]
    assert [source[item.start - 10 : item.end - 10] for item in replacements] == [
        "1 m³",
        "2 km/h",
    ]


def test_german_extended_quantity_protection_is_fail_closed():
    source = "1 m³, then 2 m³"
    replacements = _spokenform_replacements_for_run(
        source,
        "de",
        protected_spans=((0, len("1 m³")),),
    )

    assert [(item.start, item.end, item.text) for item in replacements] == [
        (11, 15, "zwei Kubikmeter")
    ]


def test_german_extended_quantity_preparation_is_idempotent():
    normalizer = GermanNormalizer()
    prepared = normalizer("1 m², 2 m³, 1 km/h")

    assert normalizer(prepared) == prepared


def test_german_extended_quantity_runs_remain_language_isolated(monkeypatch):
    source = "1 m³ and 2 m³"
    tokens = tokenize_with_offsets(source, lang="de", keep_punct=True)
    for token in tokens:
        if token.char_start >= source.index("2 m³"):
            token.lang = "en-us"

    real_adapter = pipeline_api._spokenform_replacements_for_run
    calls = []

    def record_call(text, language, **kwargs):
        calls.append((text, language))
        return real_adapter(text, language, **kwargs)

    monkeypatch.setattr(pipeline_api, "_spokenform_replacements_for_run", record_call)
    replaced, warnings = _apply_structured_replacements_to_tokens(tokens, source, "de")

    assert calls == [("1 m³ and", "de"), ("2 m³", "en-us")]
    assert not warnings
    assert any(token.extended_text == "ein Kubikmeter" for token in replaced)
    assert any(token.extended_text == "two cubic meters" for token in replaced)


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

    assert result.extended_text.startswith("3°C neben vier Grad Celsius")
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
