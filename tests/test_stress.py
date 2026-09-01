"""Tests for shared relative phoneme stress processing."""

import pytest

from kokorog2p.en.lexicon import apply_stress as english_apply_stress
from kokorog2p.stress import (
    InvalidStressLevel,
    apply_stress,
    parse_stress_level,
)

ENGLISH_VOWELS = frozenset("AIOQWYaiuæɑɒɔəɛɜɪʊʌᵻ")
GERMAN_VOWELS = frozenset("aɑeɛiɪoɔøœuʊyəɜɐIWAOQY")


@pytest.mark.parametrize(
    ("phonemes", "stress", "expected"),
    (
        ("hˈɛlˌO", -2, "hɛlO"),
        ("tsvˈaɪ", -1, "tsvˌaɪ"),
        ("kˌæt", -1, "kæt"),
        ("kæt", 1, "kˌæt"),
        ("kˌæt", 1, "kˈæt"),
        ("kæt", 2, "kˈæt"),
        ("kˈæt", 2, "kˈæt"),
    ),
)
def test_shared_helper_matches_english_parity(phonemes, stress, expected):
    assert apply_stress(phonemes, stress, vowels=ENGLISH_VOWELS) == expected
    assert english_apply_stress(phonemes, stress) == expected


@pytest.mark.parametrize("phonemes", [None, "", "kst"])
def test_shared_helper_noops_without_vowels(phonemes):
    assert apply_stress(phonemes, 2, vowels=ENGLISH_VOWELS) == phonemes


@pytest.mark.parametrize(
    ("phonemes", "stress", "expected"),
    (
        ("ʦvI", 1, "ʦvˌI"),
        ("ʦvI", 2, "ʦvˈI"),
        ("fyːɐ", 1, "fˌyːɐ"),
        ("fyːɐ", 2, "fˈyːɐ"),
        ("ʦvœlf", 1, "ʦvˌœlf"),
        ("ʦvœlf", 2, "ʦvˈœlf"),
        ("tsvˈaɪ", -1, "tsvˌaɪ"),
        ("tsvˈaɪ", -2, "tsvaɪ"),
        ("tsvˈaɪ", 2, "tsvˈaɪ"),
    ),
)
def test_german_profile_cases(phonemes, stress, expected):
    assert apply_stress(phonemes, stress, vowels=GERMAN_VOWELS) == expected


@pytest.mark.parametrize("value", ["high", "low", "++2", "3", "-3", "1.5"])
def test_invalid_stress_values_raise(value):
    with pytest.raises(InvalidStressLevel):
        parse_stress_level(value)


@pytest.mark.parametrize(
    ("value, expected"),
    [("-2", -2.0), ("-1", -1.0), ("+1", 1.0), ("+2", 2.0)],
)
def test_public_stress_values_parse(value, expected):
    assert parse_stress_level(value) == expected


def test_none_stress_parses_to_none():
    assert parse_stress_level(None) is None
