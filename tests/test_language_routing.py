"""Tests for native automatic pronunciation-language routing."""

from __future__ import annotations

from kokorog2p.language_pairs.de_en import decompose_token
from kokorog2p.language_routing import LanguageRoutingConfig, route_languages
from kokorog2p.types import TokenSpan


class FakeG2P:
    def __init__(self, table: dict[str, str]) -> None:
        self.table = table

    def lookup(self, word: str) -> str | None:
        return self.table.get(word.casefold())


def _route(text: str, tables: dict[str, dict[str, str]], *, fixed: bool = False):
    g2ps = {language: FakeG2P(table) for language, table in tables.items()}
    tokens = [TokenSpan(text, 0, len(text))]
    return route_languages(
        text,
        tokens,
        default_language="de-de",
        config=LanguageRoutingConfig(mode="auto", languages=("de", "en")),
        resolve_g2p=g2ps.__getitem__,
        target_model="1.0",
        fixed_target_model=fixed,
    )


def test_language_configuration_is_canonical_and_allowlisted() -> None:
    config = LanguageRoutingConfig(mode="auto", languages=("de", "en", "en-us"))
    assert config.languages == ("de-de", "en-us")


def test_unique_foreign_lexicon_hit_routes_without_fallback_evidence() -> None:
    result = _route("File", {"de-de": {}, "en-us": {"file": "f"}})
    assert [(token.text, token.lang) for token in result.tokens] == [("File", "en-us")]
    assert result.routes[0].fragments[0].source == "auto"


def test_default_lexicon_ownership_wins() -> None:
    result = _route("File", {"de-de": {"file": "d"}, "en-us": {"file": "f"}})
    assert result.tokens[0].lang is None


def test_fixed_target_rejects_invalid_foreign_pronunciation() -> None:
    result = _route("File", {"de-de": {}, "en-us": {"file": "§"}}, fixed=True)
    assert result.tokens[0].lang is None


def test_de_en_compound_and_morphology_examples() -> None:
    tables = {
        "de-de": {"diskussion": "d"},
        "en-us": {"manpower": "m", "cancel": "c", "download": "w"},
    }
    for word, expected in {
        "Manpowerdiskussion": [("Manpower", "en-us"), ("diskussion", "de-de")],
        "gecancelt": [("ge", "de-de"), ("cancel", "en-us"), ("t", "de-de")],
        "downloaden": [("download", "en-us"), ("en", "de-de")],
    }.items():
        result = _route(word, tables)
        assert [(token.text, token.lang) for token in result.tokens] == expected


def test_native_german_verbs_are_not_decomposed() -> None:
    tables = {"de-de": {}, "en-us": {"wart": "w", "ler": "l"}}
    for word in ("gehen", "lernen", "warten", "reden", "kennen"):
        token = TokenSpan(word, 0, len(word))
        assert (
            decompose_token(
                token,
                default_language="de-de",
                candidate_languages=("de-de", "en-us"),
                lookup=lambda language, value: tables[language].get(value),
            )
            is None
        )
