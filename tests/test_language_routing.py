"""Tests for selected-lexicon automatic pronunciation-language routing."""

from __future__ import annotations

from kokorog2p.language_codes import supported_languages
from kokorog2p.language_pairs.de_en import decompose_token
from kokorog2p.language_routing import LanguageRoutingConfig, route_languages
from kokorog2p.lexicons.evidence import LexiconEvidence
from kokorog2p.types import TokenSpan


class FakeG2P:
    def __init__(self, language: str, table: dict[str, str]) -> None:
        self.language = language
        self.table = table
        self.evidence_calls = 0
        self.lookup_calls = 0

    def lexicon_evidence(self, word: str, tag: str | None = None):
        self.evidence_calls += 1
        value = self.table.get(word.casefold())
        if value is None:
            return None
        return LexiconEvidence(
            language=self.language,
            lexicon_id=f"{self.language}:gold",
            pronunciation=value,
            kind="pronunciation",
            rating=4,
        )

    def lookup(self, word: str) -> str | None:
        self.lookup_calls += 1
        return self.table.get(word.casefold())


def _route(
    text: str,
    tables: dict[str, dict[str, str]],
    *,
    fixed: bool = False,
    protected_ranges: tuple[tuple[int, int], ...] = (),
):
    g2ps = {language: FakeG2P(language, table) for language, table in tables.items()}
    tokens = [TokenSpan(text, 0, len(text))]
    result = route_languages(
        text,
        tokens,
        default_language="de-de",
        config=LanguageRoutingConfig(mode="auto", languages=("de", "en")),
        resolve_g2p=g2ps.__getitem__,
        target_model="1.0",
        fixed_target_model=fixed,
        protected_ranges=protected_ranges,
    )
    return result, g2ps


class EvidenceFakeG2P:
    def __init__(self, language: str, table: dict[str, LexiconEvidence]) -> None:
        self.language = language
        self.table = table

    def lexicon_evidence(self, word: str, tag: str | None = None):
        del tag
        return self.table.get(word.casefold())

    def lookup(self, word: str) -> str | None:
        evidence = self.table.get(word.casefold())
        return None if evidence is None else evidence.pronunciation


def _evidence(language: str, word: str, *, marker: bool = False) -> LexiconEvidence:
    return LexiconEvidence(
        language,
        f"{language}:gold",
        f"{word}-phonemes",
        "pronunciation",
        rating=4,
        metadata={
            "pronunciation_language_markers": (
                [{"language": "en", "ipa_offset": 0}] if marker else []
            )
        },
    )


def _route_evidence(text: str, tables: dict[str, dict[str, LexiconEvidence]]):
    g2ps = {
        language: EvidenceFakeG2P(language, table) for language, table in tables.items()
    }
    return route_languages(
        text,
        [TokenSpan(text, 0, len(text))],
        default_language="de-de",
        config=LanguageRoutingConfig(mode="auto", languages=("de", "en")),
        resolve_g2p=g2ps.__getitem__,
        target_model="1.0",
    )


def test_marker_backed_whole_token_collision_beats_default_only_when_marked() -> None:
    result = _route_evidence(
        "cancel",
        {
            "de-de": {"cancel": _evidence("de-de", "cancel", marker=True)},
            "en-us": {"cancel": _evidence("en-us", "cancel")},
        },
    )
    assert [(token.text, token.lang) for token in result.tokens] == [
        ("cancel", "en-us")
    ]
    assert "foreign pronunciation confirmed" in result.routes[0].reason

    unmarked = _route_evidence(
        "File",
        {
            "de-de": {"file": _evidence("de-de", "file")},
            "en-us": {"file": _evidence("en-us", "file")},
        },
    )
    assert [(token.text, token.lang) for token in unmarked.tokens] == [("File", None)]


def test_marker_backed_morphology_requires_default_stem_evidence() -> None:
    gecancelt = _route_evidence(
        "gecancelt",
        {
            "de-de": {
                "gecancelt": _evidence("de-de", "gecancelt"),
                "cancel": _evidence("de-de", "cancel", marker=True),
            },
            "en-us": {"cancel": _evidence("en-us", "cancel")},
        },
    )
    assert [(token.text, token.lang) for token in gecancelt.tokens] == [
        ("ge", "de-de"),
        ("cancel", "en-us"),
        ("t", "de-de"),
    ]

    downloaden = _route_evidence(
        "downloaden",
        {
            "de-de": {
                "downloaden": _evidence("de-de", "downloaden", marker=True),
                "download": _evidence("de-de", "download"),
            },
            "en-us": {"download": _evidence("en-us", "download")},
        },
    )
    assert [(token.text, token.lang) for token in downloaden.tokens] == [
        ("download", "en-us"),
        ("en", "de-de"),
    ]


def test_unmarked_starten_collision_stays_german() -> None:
    result = _route_evidence(
        "starten",
        {
            "de-de": {
                "starten": _evidence("de-de", "starten"),
                "start": _evidence("de-de", "start"),
            },
            "en-us": {"start": _evidence("en-us", "start")},
        },
    )
    assert [(token.text, token.lang) for token in result.tokens] == [("starten", None)]


def test_default_fragment_preserves_nonzero_document_offset() -> None:
    german = EvidenceFakeG2P("de-de", {"wort": _evidence("de-de", "wort")})
    english = EvidenceFakeG2P("en-us", {})
    result = route_languages(
        "xx Wort",
        [TokenSpan("Wort", 3, 7)],
        default_language="de-de",
        config=LanguageRoutingConfig(mode="auto", languages=("de", "en")),
        resolve_g2p={"de-de": german, "en-us": english}.__getitem__,
        target_model="1.0",
    )
    fragment = result.routes[0].fragments[0]
    assert fragment.text == "Wort"
    assert fragment.text == "xx Wort"[fragment.char_start : fragment.char_end]


def test_language_configuration_is_canonical_and_allowlisted() -> None:
    config = LanguageRoutingConfig(mode="auto", languages=("de", "en", "en-us"))
    assert config.languages == ("de-de", "en-us")


def test_language_inventory_includes_all_benchmark_variants() -> None:
    expected = {
        "en-us",
        "en-gb",
        "de-de",
        "fr-fr",
        "es-es",
        "it-it",
        "pt-br",
        "pt-pt",
        "cs-cz",
        "vi-vn",
        "sv-se",
        "ru-ru",
        "kk",
        "hi-in",
        "he",
        "ar",
        "zh",
        "ja-jp",
        "ko-kr",
        "th-th",
    }
    assert expected.issubset(set(supported_languages()))
    assert LanguageRoutingConfig(
        mode="auto", languages=("pt-pt", "en-gb")
    ).languages == ("pt-pt", "en-gb")
    assert LanguageRoutingConfig(mode="auto", languages=("hi", "en")).languages == (
        "hi-in",
        "en-us",
    )


def test_all_language_allowlist_resolves_each_frontend_once() -> None:
    languages = supported_languages()
    constructed: list[str] = []
    frontends: dict[str, FakeG2P] = {}
    tables = {language: {} for language in languages}
    tables["en-us"] = {"file": "f"}

    def resolve(language: str) -> FakeG2P:
        constructed.append(language)
        frontend = FakeG2P(language, tables[language])
        frontends[language] = frontend
        return frontend

    text = "File File"
    result = route_languages(
        text,
        [TokenSpan("File", 0, 4), TokenSpan("File", 5, 9)],
        default_language="de-de",
        config=LanguageRoutingConfig(mode="auto", languages=languages),
        resolve_g2p=resolve,
        target_model="1.0",
    )

    assert [token.lang for token in result.tokens] == ["en-us", "en-us"]
    assert sorted(constructed) == sorted(languages)
    assert len(constructed) == len(set(constructed)) == len(languages)
    evidence_counts = {
        language: frontend.evidence_calls for language, frontend in frontends.items()
    }
    assert evidence_counts == {language: 1 for language in languages}
    assert all(frontend.lookup_calls == 0 for frontend in frontends.values())


def test_unique_foreign_selected_hit_routes_with_provenance() -> None:
    result, _ = _route("File", {"de-de": {}, "en-us": {"file": "f"}})
    assert [(token.text, token.lang) for token in result.tokens] == [("File", "en-us")]
    assert result.routes[0].fragments[0].source == "auto"
    assert result.routes[0].fragments[0].evidence_lexicon_id == "en-us:gold"


def test_default_lexicon_ownership_wins_collisions() -> None:
    result, _ = _route("File", {"de-de": {"file": "d"}, "en-us": {"file": "f"}})
    assert result.tokens[0].lang is None
    assert result.routes[0].fragments[0].evidence_lexicon_id == "de-de:gold"


def test_fixed_target_rejects_invalid_foreign_pronunciation_after_evidence() -> None:
    result, g2ps = _route("File", {"de-de": {}, "en-us": {"file": "§"}}, fixed=True)
    assert result.tokens[0].lang is None
    assert "incompatible" in result.warnings[0]
    assert g2ps["en-us"].evidence_calls == 1
    assert g2ps["en-us"].lookup_calls == 1


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
        result, _ = _route(word, tables)
        assert [(token.text, token.lang) for token in result.tokens] == expected


def test_native_german_verbs_are_not_decomposed_by_generic_rules() -> None:
    tables = {"de-de": {}, "en-us": {"wart": "w", "ler": "l"}}
    for word in ("gehen", "lernen", "warten", "reden", "kennen"):
        token = TokenSpan(word, 0, len(word))
        assert (
            decompose_token(
                token,
                default_language="de-de",
                candidate_languages=("de-de", "en-us"),
                evidence=lambda language, value: (
                    LexiconEvidence(language, f"{language}:gold", "p", "pronunciation")
                    if value in tables.get(language, {})
                    else None
                ),
            )
            is None
        )


def test_protected_override_range_blocks_automatic_routing() -> None:
    result, _ = _route(
        "File",
        {"de-de": {}, "en-us": {"file": "f"}},
        protected_ranges=((0, 4),),
    )
    assert result.tokens[0].lang is None
    assert result.routes == ()
