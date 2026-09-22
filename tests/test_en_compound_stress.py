from kokorog2p.en.realization import resolve_compound_stress
from kokorog2p.en.subtokens import EnglishSubtoken


def test_compound_keeps_strongest_primary_stress() -> None:
    tokens = [
        EnglishSubtoken("black", 0, 5, "ˈblæk"),
        EnglishSubtoken("bird", 5, 9, "ˈbɜɹd"),
    ]
    resolve_compound_stress(tokens)
    assert tokens[0].phonemes == "ˈblæk"
    assert tokens[1].phonemes == "ˌbɜɹd"


def test_single_letter_first_subtoken_is_not_compound_anchor() -> None:
    tokens = [
        EnglishSubtoken("A", 0, 1, "ˈA"),
        EnglishSubtoken("Word", 1, 5, "ˈwɜɹd"),
    ]
    resolve_compound_stress(tokens)
    assert tokens[0].phonemes == "ˌA"
    assert tokens[1].phonemes == "ˈwɜɹd"


def test_compound_resolution_is_profile_controlled() -> None:
    from kokorog2p.en.phoneme_codec import EnglishFrontendProfile

    tokens = [
        EnglishSubtoken("black", 0, 5, "ˈblæk"),
        EnglishSubtoken("bird", 5, 9, "ˈbɜɹd"),
    ]
    resolve_compound_stress(
        tokens,
        profile=EnglishFrontendProfile("disabled", resolve_compound_stress=False),
    )
    assert [token.phonemes for token in tokens] == ["ˈblæk", "ˈbɜɹd"]
