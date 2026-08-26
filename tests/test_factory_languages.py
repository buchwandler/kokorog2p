"""Regression tests for native language factory routing."""

import pytest

from kokorog2p import get_g2p, phonemize
from kokorog2p.cs import CzechG2P
from kokorog2p.es import SpanishG2P
from kokorog2p.it import ItalianG2P
from kokorog2p.pt import PortugueseG2P
from kokorog2p.types import OverrideSpan


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        ("es", SpanishG2P),
        ("es-es", SpanishG2P),
        ("spa", SpanishG2P),
        ("spanish", SpanishG2P),
        ("it", ItalianG2P),
        ("it-it", ItalianG2P),
        ("ita", ItalianG2P),
        ("italian", ItalianG2P),
        ("pt", PortugueseG2P),
        ("pt-br", PortugueseG2P),
        ("pt-pt", PortugueseG2P),
        ("por", PortugueseG2P),
        ("portuguese", PortugueseG2P),
        ("cs", CzechG2P),
        ("cs-cz", CzechG2P),
        ("ces", CzechG2P),
        ("czech", CzechG2P),
    ],
)
def test_native_factory_routing(language: str, expected: type) -> None:
    g2p = get_g2p(
        language,
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        load_gold=False,
        load_silver=False,
    )

    assert isinstance(g2p, expected)


@pytest.mark.parametrize(
    ("language", "expected_dialect", "expected_number"),
    [
        ("pt", "br", "dezesseis"),
        ("pt-br", "br", "dezesseis"),
        ("pt-pt", "pt", "dezasseis"),
    ],
)
def test_portuguese_factory_routes_spokenform_dialect(
    language: str, expected_dialect: str, expected_number: str
) -> None:
    g2p = get_g2p(
        language,
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        load_gold=False,
        load_silver=False,
    )

    assert g2p.dialect == expected_dialect
    assert g2p._normalizer("16") == expected_number


@pytest.mark.parametrize(
    ("language", "text"),
    [("es", "Hola"), ("it", "Ciao"), ("pt", "Olá")],
)
def test_top_level_phonemize_for_native_rule_languages(
    language: str, text: str
) -> None:
    result = phonemize(
        text,
        language=language,
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        return_ids=False,
    )

    assert result.phonemes
    assert not any("failed to load" in warning.lower() for warning in result.warnings)


@pytest.mark.parametrize(
    ("language", "text", "override"),
    [
        ("es", "Hola Ciao", OverrideSpan(5, 9, {"lang": "it"})),
        ("it", "Ciao Hola", OverrideSpan(5, 9, {"lang": "es"})),
        ("pt", "Olá Ciao", OverrideSpan(4, 8, {"lang": "it"})),
    ],
)
def test_mixed_language_overrides_use_native_factories(
    language: str, text: str, override: OverrideSpan
) -> None:
    result = phonemize(
        text,
        language=language,
        overrides=[override],
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        return_ids=False,
    )

    switched = [
        token
        for token in result.tokens
        if token.char_start >= override.char_start
        and token.char_end <= override.char_end
    ]
    assert switched
    assert all(token.lang == override.attrs["lang"] for token in switched)
    assert all(token.meta.get("phonemes") for token in switched)


def test_arabic_factory_aliases_and_native_profile() -> None:
    from kokorog2p.ar import ArabicG2P

    instances = [
        get_g2p(alias, diacritizer="none")
        for alias in ("ar", "ara", "arabic", "ar-msa", "msa", "ar-sa")
    ]
    assert all(isinstance(instance, ArabicG2P) for instance in instances)
    assert len({id(instance) for instance in instances}) == 1
    assert instances[0].version == "1.0"
    assert instances[0].get_target_model() == "nabra-82m-v0.1"


def test_arabic_espeak_backend_remains_generic() -> None:
    from kokorog2p.espeak_g2p import EspeakOnlyG2P

    assert isinstance(get_g2p("ar", backend="espeak"), EspeakOnlyG2P)


def test_top_level_g2p_options_configure_arabic() -> None:
    result = phonemize(
        "مَرْحَبًا",
        language="ar",
        g2p_options={"diacritizer": "none"},
        return_ids=True,
    )
    assert result.phonemes
    assert result.token_ids
