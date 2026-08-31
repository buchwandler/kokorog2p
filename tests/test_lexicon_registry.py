from kokorog2p.lexicons import (
    available_lexicons,
    get_lexicon_spec,
    normalize_lexicon_selection,
)


def test_registry_aliases_and_order() -> None:
    assert available_lexicons("en") == ("gold", "silver")
    assert available_lexicons("english") == ("gold", "silver")
    assert available_lexicons("ja_jp") == ("words",)
    assert get_lexicon_spec("en-us", "gold").rating == 4


def test_german_third_party_lexicons_are_opt_in_and_selectable() -> None:
    assert available_lexicons("de") == ("gold", "crane", "espeak", "olaph")
    assert (
        available_lexicons("de-de")
        == available_lexicons("de_DE")
        == available_lexicons("german")
    )

    for name in ("crane", "espeak", "olaph"):
        spec = get_lexicon_spec("de", name)
        assert spec.default_priority is None
        assert spec.phoneme_encoding == "ipa"

    assert normalize_lexicon_selection("de", None) == ("gold",)
    assert normalize_lexicon_selection("de", "espeak") == ("espeak",)
    assert normalize_lexicon_selection("de", "olaph") == ("olaph",)


def test_registry_tier_metadata() -> None:
    assert get_lexicon_spec("en-us", "silver").rating == 3


def test_unknown_name_lists_valid_names() -> None:
    try:
        get_lexicon_spec("en-us", "missing")
    except ValueError as exc:
        assert "gold" in str(exc) and "silver" in str(exc)
    else:
        raise AssertionError("unknown lexicon was accepted")
