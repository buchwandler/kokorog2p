"""Tests for positive selected-lexicon evidence."""

from types import SimpleNamespace

from lexphon import (
    PronunciationLanguageMarker,
    PronunciationToken,
    PronunciationVariant,
)

from kokorog2p.base import G2PBase
from kokorog2p.de.g2p import GermanG2P
from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.fr.g2p import FrenchG2P
from kokorog2p.lexicons.evidence import LexiconEvidence, evidence_from_lexphon_token
from kokorog2p.lexicons.runtime import LexiconHit
from kokorog2p.token import GToken


class MinimalG2P(G2PBase):
    def __call__(self, text: str) -> list[GToken]:
        return []

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        return None


def test_base_evidence_default_is_none() -> None:
    assert MinimalG2P().lexicon_evidence("anything") is None


def test_evidence_is_canonical_immutable_and_serializable() -> None:
    evidence = LexiconEvidence(
        language="DE",
        lexicon_id="de-de:gold",
        pronunciation="haʊs",
        kind="pronunciation",
        metadata={"source": "gold"},
    )
    assert evidence.language == "de-de"
    assert dict(evidence.metadata or {}) == {"source": "gold"}
    assert evidence.as_dict()["lexicon_id"] == "de-de:gold"
    try:
        evidence.language = "en-us"  # type: ignore[misc]
    except AttributeError:
        pass
    else:
        raise AssertionError("evidence must be immutable")


def test_english_evidence_uses_exact_selected_hit_only() -> None:
    hit = LexiconHit(
        value="hɛloʊ",
        name="gold",
        rating=4,
        kind="pronunciation",
        phoneme_encoding="ipa",
        lexicon_id="en-us:gold",
        metadata={"selected": True},
    )
    lexicon = SimpleNamespace(
        lookup_hit=lambda word: hit if word == "hello" else None,
        pronunciation_from_hit=lambda selected, tag: selected.value,
    )
    g2p = EnglishG2P.__new__(EnglishG2P)
    g2p.language = "en-us"
    g2p.lexicon = lexicon
    evidence = g2p.lexicon_evidence("hello")
    assert evidence is not None
    assert evidence.lexicon_id == "en-us:gold"
    assert evidence.pronunciation == "hɛloʊ"
    assert g2p.lexicon_evidence("proper-noun-fallback") is None


def test_german_evidence_requires_known_structured_token() -> None:
    token = PronunciationToken(
        text="Haus",
        pronunciation="hˈaʊs",
        source="gold",
        lexicon_id="de-de:gold",
        variants=("hˈaʊs", "haʊs"),
        selector_tag="NOUN",
    )
    lexicon = SimpleNamespace(
        lexicons=("gold",),
        lookup_token=lambda word, tag=None: token if word == "Haus" else None,
    )
    g2p = GermanG2P.__new__(GermanG2P)
    g2p.language = "de-de"
    g2p._lexicon = lexicon
    evidence = g2p.lexicon_evidence("Haus", "NN")
    assert evidence is not None
    assert evidence.lexicon_id == "de-de:gold"
    assert evidence.metadata["selector_tag"] == "NOUN"


def test_german_rule_only_frontend_has_no_evidence() -> None:
    g2p = GermanG2P.__new__(GermanG2P)
    g2p.language = "de-de"
    g2p._lexicon = None
    assert g2p.lexicon_evidence("Haus") is None


def test_lexphon_evidence_serializes_released_language_markers() -> None:
    token = PronunciationToken(
        text="download",
        pronunciation="dˈaʊnləʊd",
        source="lexicon",
        lexicon_id="de-de:gold",
        variant_details=(
            PronunciationVariant(
                pronunciation="dˈaʊnləʊd",
                source_pronunciation="(en)dˈaʊnləʊd(de)",
                language_markers=(
                    PronunciationLanguageMarker("en", 0),
                    PronunciationLanguageMarker("de", 10),
                ),
            ),
        ),
    )
    evidence = evidence_from_lexphon_token(
        language="de-de", token=token, selected_lexicons=("gold",)
    )
    assert evidence is not None
    assert evidence.rating == 4
    assert evidence.metadata["source_pronunciation"] == "(en)dˈaʊnləʊd(de)"
    assert evidence.metadata["pronunciation_language_markers"] == [
        {"language": "en", "ipa_offset": 0},
        {"language": "de", "ipa_offset": 10},
    ]


def test_french_evidence_uses_selected_hit_not_builtin_fix() -> None:
    hit = LexiconHit(
        value="dəmɑ̃de",
        name="gold",
        rating=4,
        kind="pronunciation",
        phoneme_encoding="ipa",
        lexicon_id="fr-fr:gold",
        metadata={"selected": True},
    )
    lexicon = SimpleNamespace(
        lookup_hit=lambda word: hit if word == "demander" else None,
        pronunciation_from_hit=lambda selected, tag: selected.value,
    )
    g2p = FrenchG2P.__new__(FrenchG2P)
    g2p.language = "fr-fr"
    g2p.lexicon = lexicon
    evidence = g2p.lexicon_evidence("demander")
    assert evidence is not None
    assert evidence.lexicon_id == "fr-fr:gold"
    assert g2p.lexicon_evidence("monsieur") is None


def test_lexphon_evidence_requires_selected_trustworthy_provenance() -> None:
    token = PronunciationToken(
        text="слово",
        pronunciation="sloˈvo",
        source="lexhint",
        lexicon_id="ru:lexhint",
    )
    evidence = evidence_from_lexphon_token(
        language="ru-ru", token=token, selected_lexicons=("ru:lexhint",)
    )
    assert evidence is not None
    assert evidence.language == "ru-ru"
    assert evidence.lexicon_id == "ru:lexhint"

    unknown = PronunciationToken("слово", None, "lexhint", lexicon_id="ru:lexhint")
    assert (
        evidence_from_lexphon_token(
            language="ru-ru",
            token=unknown,
            selected_lexicons=("ru:lexhint",),
        )
        is None
    )
    ambiguous = PronunciationToken("слово", "p", "other-source", lexicon_id=None)
    assert (
        evidence_from_lexphon_token(
            language="ru-ru",
            token=ambiguous,
            selected_lexicons=("ru:lexhint", "ru:other"),
        )
        is None
    )


def test_rule_only_frontends_do_not_claim_lexicon_evidence() -> None:
    from kokorog2p.ar.g2p import ArabicG2P
    from kokorog2p.cs.g2p import CzechG2P
    from kokorog2p.es.g2p import SpanishG2P
    from kokorog2p.he.g2p import HebrewG2P
    from kokorog2p.it.g2p import ItalianG2P
    from kokorog2p.kk.g2p import KazakhG2P
    from kokorog2p.zh.g2p import ChineseG2P

    for frontend in (
        SpanishG2P,
        ItalianG2P,
        CzechG2P,
        HebrewG2P,
        ArabicG2P,
        ChineseG2P,
        KazakhG2P,
    ):
        instance = frontend.__new__(frontend)
        assert instance.lexicon_evidence("example") is None
