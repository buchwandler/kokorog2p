"""Structural Vietnamese syllable parser tests."""

import pytest

from kokorog2p.vi.syllable import (
    InvalidVietnameseSyllable,
    VietnameseTone,
    is_vietnamese_syllable,
    parse_syllable,
)


@pytest.mark.parametrize(
    "word",
    [
        "ba",
        "cha",
        "da",
        "đa",
        "ga",
        "ghê",
        "gia",
        "ha",
        "kê",
        "kha",
        "la",
        "ma",
        "na",
        "nga",
        "nghe",
        "nha",
        "pha",
        "qua",
        "ra",
        "sa",
        "ta",
        "tha",
        "tra",
        "va",
        "xa",
    ],
)
def test_supported_onset_families(word: str) -> None:
    assert is_vietnamese_syllable(word)
    assert parse_syllable(word).nucleus


@pytest.mark.parametrize("word", ["ba", "bà", "bả", "bã", "bá", "bạ"])
def test_six_named_tones(word: str) -> None:
    assert parse_syllable(word).tone in set(VietnameseTone)


@pytest.mark.parametrize(
    ("word", "nucleus", "coda"),
    [
        ("ăn", "ă", "n"),
        ("âm", "â", "m"),
        ("tiếng", "iê", "ng"),
        ("mưa", "ưa", None),
        ("người", "ươ", "i"),
        ("muốn", "uô", "n"),
        ("hoa", "a", None),
        ("mai", "a", "i"),
        ("sao", "a", "o"),
        ("anh", "a", "nh"),
        ("học", "o", "c"),
    ],
)
def test_rime_and_coda_structure(word: str, nucleus: str, coda: str | None) -> None:
    syllable = parse_syllable(word)
    assert syllable.nucleus == nucleus
    assert syllable.coda == coda


@pytest.mark.parametrize("word", ["qá", "cê", "kà", "ghá", "ngha", "bànn", "bà́"])
def test_invalid_conditioned_spellings_are_rejected(word: str) -> None:
    assert not is_vietnamese_syllable(word)
    with pytest.raises((InvalidVietnameseSyllable, ValueError)):
        parse_syllable(word)


def test_checked_codas_restrict_tones() -> None:
    assert is_vietnamese_syllable("bác")
    assert is_vietnamese_syllable("bạc")
    assert not is_vietnamese_syllable("bàc")
