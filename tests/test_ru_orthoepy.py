from kokorog2p.ru.orthoepy import (
    apply_orthoepy,
    find_stressed_vowel_ordinal,
    reattach_stress_by_vowel_ordinal,
)


def test_final_ogo_ego_rule_preserves_stress_ordinal():
    result = apply_orthoepy("ново́го")
    assert result.rewritten == "ново́во"
    assert "final-ogo-ego-v" in result.applied_rules


def test_lexical_g_exception_and_silent_clusters():
    assert apply_orthoepy("мно́го").rewritten == "мно́го"
    assert apply_orthoepy("се́рдце").rewritten == "се́рце"
    assert apply_orthoepy("со́лнце").rewritten == "со́нце"


def test_lexical_chn_rule_is_not_global():
    assert apply_orthoepy("ко́нечно").rewritten == "ко́нешно"
    assert apply_orthoepy("то́чно").rewritten == "то́чно"


def test_stress_ordinal_helpers():
    assert find_stressed_vowel_ordinal("бе́лого") == 0
    assert reattach_stress_by_vowel_ordinal("белова", 1) == "бело́ва"
