"""Tests for positive selected-lexicon evidence."""

from types import SimpleNamespace

from lexphon import PronunciationToken

from kokorog2p.base import G2PBase
from kokorog2p.de.g2p import GermanG2P
from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.lexicons.evidence import LexiconEvidence
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
