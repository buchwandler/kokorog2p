"""Unicode and tone invariants for the native Vietnamese frontend."""

import unicodedata

import pytest

from kokorog2p.vi.syllable import VietnameseTone, parse_syllable
from kokorog2p.vi.unicode import (
    InvalidVietnameseSyllable,
    decompose_vietnamese,
    extract_tone,
    normalize_vietnamese,
    remove_tone_marks,
)


@pytest.mark.parametrize(
    ("word", "tone"),
    [
        ("ba", VietnameseTone.NGANG),
        ("bà", VietnameseTone.HUYEN),
        ("bả", VietnameseTone.HOI),
        ("bã", VietnameseTone.NGA),
        ("bá", VietnameseTone.SAC),
        ("bạ", VietnameseTone.NANG),
    ],
)
def test_named_tone_extraction(word: str, tone: VietnameseTone) -> None:
    extracted = extract_tone(word)
    assert extracted.tone is tone
    assert extracted.normalized == "ba"
    assert remove_tone_marks(word) == "ba"


def test_nfc_and_nfd_are_canonically_equivalent() -> None:
    word = "tiếng"
    assert normalize_vietnamese(word) == normalize_vietnamese(
        unicodedata.normalize("NFD", word)
    )
    assert decompose_vietnamese(word) == unicodedata.normalize("NFD", word)
    assert parse_syllable(word).tone is VietnameseTone.SAC


def test_quality_marks_survive_tone_extraction() -> None:
    assert extract_tone("ắ").normalized == "ă"
    assert extract_tone("ế").normalized == "ê"
    assert extract_tone("ở").normalized == "ơ"


def test_uppercase_and_d_handling() -> None:
    assert parse_syllable("ĐI").onset == "đ"
    assert parse_syllable("ĐI").nucleus == "i"


def test_multiple_or_misplaced_tone_marks_are_rejected() -> None:
    with pytest.raises(InvalidVietnameseSyllable):
        extract_tone("ba\u0301\u0300")
    with pytest.raises(InvalidVietnameseSyllable):
        extract_tone("b\u0301a")
