from kokorog2p.sv import SwedishRuleEngine, phonemize_word_raw, to_kokoro


def test_normalization_is_case_insensitive_and_nfc_based() -> None:
    assert phonemize_word_raw("HEJ").ipa == phonemize_word_raw("hej").ipa
    assert phonemize_word_raw("Å").word == "å"


def test_swedish_letters_have_raw_ipa() -> None:
    for letter in "åäöé":
        result = phonemize_word_raw(letter)
        assert result.word == letter
        assert result.phones


def test_longest_match_graphemes_and_trace() -> None:
    result = phonemize_word_raw("skjuta", trace=True)
    assert result.phones[0] == "ɧ"
    assert "SV-C-001-SKJ" in result.rule_ids

    result = phonemize_word_raw("tjugo", trace=True)
    assert result.phones[0] == "ɕ"
    assert "SV-C-010-TJ" in result.rule_ids


def test_soft_and_hard_consonant_branches() -> None:
    soft_g = phonemize_word_raw("ge", trace=True)
    hard_g = phonemize_word_raw("ga", trace=True)
    soft_k = phonemize_word_raw("ke", trace=True)
    hard_k = phonemize_word_raw("ka", trace=True)
    soft_sk = phonemize_word_raw("ske", trace=True)
    hard_sk = phonemize_word_raw("ska", trace=True)
    assert "SV-C-100-SOFT-G" in soft_g.rule_ids
    assert "SV-C-101-HARD-G" in hard_g.rule_ids
    assert "SV-C-110-SOFT-K" in soft_k.rule_ids
    assert "SV-C-111-HARD-K" in hard_k.rule_ids
    assert "SV-C-120-SOFT-SK" in soft_sk.rule_ids
    assert "SV-C-121-HARD-SK" in hard_sk.rule_ids


def test_quantity_and_stress_are_explicit_phases() -> None:
    long_vowel = phonemize_word_raw("tak", trace=True)
    short_vowel = phonemize_word_raw("tack", trace=True)
    assert "ː" in long_vowel.ipa
    assert "ː" not in short_vowel.ipa
    assert long_vowel.ipa.startswith("tˈ")
    assert any(rule.startswith("SV-V-") for rule in short_vowel.rule_ids)


def test_retroflexion_consumes_r_plus_dental() -> None:
    for spelling, phone in (
        ("rt", "ʈ"),
        ("rd", "ɖ"),
        ("rn", "ɳ"),
        ("rs", "ʂ"),
        ("rl", "ɭ"),
    ):
        result = phonemize_word_raw("a" + spelling)
        assert phone in result.phones
        assert "r" not in result.phones


def test_kokoro_adapter_is_explicit() -> None:
    assert to_kokoro("ɧʉːr") == "ʃuɹ"
    try:
        to_kokoro("☃")
    except ValueError as exc:
        assert "unsupported" in str(exc).lower()
    else:
        raise AssertionError("unsupported phones must not be silently removed")


def test_engine_is_stateless() -> None:
    engine = SwedishRuleEngine()
    assert engine.phonemize_word_raw("hej") == engine.phonemize_word_raw("hej")
