import pytest

from kokorog2p.ru.model_profile import (
    PROFILE_NAME,
    TARGET_MODEL,
    apply_russian_vowel_reduction,
    model_profile_vocab,
    normalize_espeak_symbols,
    normalize_long_shcha,
    validate_russian_symbols,
)


def test_profile_targets_stock_vocab_and_known_symbol_folds():
    assert TARGET_MODEL == "1.0"
    assert PROFILE_NAME == "KokoroRussianV2"
    assert normalize_espeak_symbols("ɫᵻɤɒ") == "lɪəɑ"
    assert model_profile_vocab() == __import__(
        "kokorog2p.vocab", fromlist=["get_vocab"]
    ).get_vocab("1.0")


def test_russian_tied_alveolopalatal_affricate_maps_to_stock_label():
    assert normalize_espeak_symbols("t͡ɕɪˈtɨrʲɪ") == "ʨɪˈtɪrʲɪ"
    assert (
        validate_russian_symbols(
            "ʨɪˈtɪrʲɪ",
            source_token="четыре",
            raw_ipa="t͡ɕɪˈtɨrʲɪ",
        )
        == []
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("t͡s", "ʦ"),
        ("t͜s", "ʦ"),
        ("t͡ɕ", "ʨ"),
        ("t͜ɕ", "ʨ"),
        ("t͡ʃ", "ʧ"),
        ("d͡z", "ʣ"),
        ("d͡ʒ", "ʤ"),
        ("d͡ʑ", "ʥ"),
        ("ʐ", "ʒ"),
    ],
)
def test_russian_known_tied_affricates_use_stock_single_labels(raw, expected):
    assert normalize_espeak_symbols(raw) == expected


def test_unknown_tied_sequence_remains_strictly_invalid():
    raw = "k͡x"
    normalized = normalize_espeak_symbols(raw)
    assert "͡" in normalized
    with pytest.raises(ValueError, match="U\\+0361"):
        validate_russian_symbols(normalized, source_token="fixture", raw_ipa=raw)


def test_vowel_reduction_positions():
    assert apply_russian_vowel_reduction("baˈo") == "bɐˈo"
    assert apply_russian_vowel_reduction("baaˈo") == "bəɐˈo"
    assert apply_russian_vowel_reduction("jɑˈo") == "jɪˈo"
    assert apply_russian_vowel_reduction("bˈoa") == "bˈoə"


def test_long_shcha_is_idempotent():
    assert normalize_long_shcha("ɕ") == "ɕː"
    assert normalize_long_shcha("ɕː") == "ɕː"


def test_unknown_symbol_is_rejected_or_reported():
    with pytest.raises(ValueError, match=r"U\+00A7"):
        validate_russian_symbols("§", source_token="слово", raw_ipa="§")
    assert validate_russian_symbols("§", strict=False) == ["§"]
