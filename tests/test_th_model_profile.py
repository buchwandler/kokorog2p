"""Tests for the isolated Wayu Thai vocabulary profile."""

from kokorog2p.th.model_profile import (
    LOW_TONE,
    TARGET_MODEL,
    TLTK_TONE_MAP,
    adapt_tltk_output,
)
from kokorog2p.vocab import (
    get_vocab,
    get_vocab_reverse,
    phonemes_to_ids,
    validate_for_kokoro,
)


def test_wayu_profile_assigns_low_tone_without_mutating_stock() -> None:
    stock = dict(get_vocab("1.0"))
    wayu = get_vocab(TARGET_MODEL)

    assert LOW_TONE not in stock
    assert wayu[LOW_TONE] == 7
    assert get_vocab("1.0") == stock
    assert get_vocab_reverse(TARGET_MODEL)[7] == LOW_TONE


def test_wayu_profile_is_isolated_from_nabra() -> None:
    nabra_before = dict(get_vocab("nabra-82m-v0.1"))
    _ = get_vocab(TARGET_MODEL)
    assert get_vocab("nabra-82m-v0.1") == nabra_before


def test_wayu_tones_validate_and_encode() -> None:
    assert set(TLTK_TONE_MAP.values()) == {"→", "˩", "↘", "↗", "↓"}
    for symbol in TLTK_TONE_MAP.values():
        valid, invalid = validate_for_kokoro(symbol, model=TARGET_MODEL)
        assert valid, invalid
    valid, invalid = validate_for_kokoro(LOW_TONE, model="1.0")
    assert not valid
    assert LOW_TONE in invalid
    assert phonemes_to_ids(LOW_TONE, model=TARGET_MODEL) == [7]


def test_tltk_adaptation_is_contextual_and_cleans_artifacts() -> None:
    assert adapt_tltk_output("a2") == "a˩"
    assert adapt_tltk_output("a3") == "a↘"
    assert adapt_tltk_output("12") == "12"
    assert adapt_tltk_output("ᴐ1|<syl>") == "ɔ→"
