from kokorog2p.th.model_profile import (
    LEXHINT_TONE_MAP,
    LOW_TONE,
    TARGET_MODEL,
    adapt_lexhint_ipa,
)
from kokorog2p.vocab import (
    get_vocab,
    get_vocab_reverse,
    phonemes_to_ids,
    validate_for_kokoro,
)


def test_wayu_profile_keeps_reserved_low_tone() -> None:
    stock = dict(get_vocab("1.0"))
    wayu = get_vocab(TARGET_MODEL)
    assert LOW_TONE not in stock
    assert wayu[LOW_TONE] == 7
    assert get_vocab("1.0") == stock
    assert get_vocab_reverse(TARGET_MODEL)[7] == LOW_TONE


def test_lexhint_tones_are_explicit_and_valid() -> None:
    assert LEXHINT_TONE_MAP["˥˩"] == "↓"
    assert adapt_lexhint_ipa("a˥˩") == "a↓"
    for symbol in set(LEXHINT_TONE_MAP.values()) | {LOW_TONE}:
        valid, invalid = validate_for_kokoro(symbol, model=TARGET_MODEL)
        assert valid, invalid
    assert phonemes_to_ids(LOW_TONE, model=TARGET_MODEL) == [7]
