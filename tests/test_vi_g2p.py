"""End-to-end Vietnamese G2P and shared pipeline tests."""

import unicodedata

import pytest

from kokorog2p import get_g2p, phonemize
from kokorog2p.token import GToken
from kokorog2p.types import OverrideSpan
from kokorog2p.vi import VietnameseG2P
from kokorog2p.vi.syllable import InvalidVietnameseSyllable


@pytest.fixture
def native() -> VietnameseG2P:
    return VietnameseG2P(foreign_fallback="none", strict=False)


def test_native_call_returns_offset_aware_gtokens(native: VietnameseG2P) -> None:
    tokens = native("Tôi là ba.")
    assert all(isinstance(token, GToken) for token in tokens)
    assert [
        (token.text, token.get("char_start"), token.get("char_end")) for token in tokens
    ] == [
        ("Tôi", 0, 3),
        ("là", 4, 6),
        ("ba", 7, 9),
        (".", 9, 10),
    ]
    assert tokens[-1].is_punctuation


def test_nfc_and_nfd_have_identical_phonemes(native: VietnameseG2P) -> None:
    source = "Tôi thấy tiếng Việt."
    assert native.phonemize(source) == native.phonemize(
        unicodedata.normalize("NFD", source)
    )


def test_ascii_only_vietnamese_is_not_sent_to_english(native: VietnameseG2P) -> None:
    result = native("ba ban mai nam lan")
    assert all(token.get("classification") == "VI_SYLLABLE" for token in result)
    assert all(token.phonemes for token in result)


def test_invalid_token_can_use_explicit_non_strict_no_fallback() -> None:
    g2p = VietnameseG2P(foreign_fallback="none", strict=False)
    assert g2p.phonemize("Python") == ""


def test_strict_none_fallback_reports_invalid_token() -> None:
    with pytest.raises(InvalidVietnameseSyllable):
        VietnameseG2P(foreign_fallback="none", strict=True).phonemize("Python")


def test_existing_english_frontend_is_lazy_foreign_fallback() -> None:
    g2p = VietnameseG2P(foreign_fallback="english", strict=True)
    assert g2p._foreign_g2p is None
    assert g2p.lookup("Python")
    assert g2p._foreign_g2p is not None


@pytest.mark.parametrize("alias", ["vi", "vi-vn", "vie", "vietnamese"])
def test_factory_aliases(alias: str) -> None:
    g2p = get_g2p(alias, use_spacy=False, foreign_fallback="none", strict=False)
    assert isinstance(g2p, VietnameseG2P)
    assert g2p.language == "vi-vn"


def test_top_level_ids_and_model_validation() -> None:
    result = phonemize(
        "Xin chào!", language="vi", return_ids=True, return_phonemes=True
    )
    assert result.phonemes
    assert result.token_ids
    assert not result.warnings


def test_vietnamese_language_override_preserves_offsets() -> None:
    result = phonemize(
        "Hello xin chào!",
        language="en-us",
        overrides=[OverrideSpan(6, 14, {"lang": "vi"})],
        return_ids=False,
    )
    switched = [
        token
        for token in result.tokens
        if token.char_start >= 6 and token.char_end <= 14
    ]
    assert switched
    assert all(token.lang == "vi" for token in switched)
    assert all(token.meta.get("phonemes") for token in switched)


def test_top_level_nfd_span_alignment_matches_nfc() -> None:
    source = "Tôi thấy tiếng Việt."
    nfd = unicodedata.normalize("NFD", source)
    assert (
        phonemize(source, language="vi").phonemes
        == phonemize(nfd, language="vi").phonemes
    )
