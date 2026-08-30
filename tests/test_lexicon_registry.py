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


def test_german_crane_is_opt_in_and_selectable() -> None:
    assert available_lexicons("de") == ("gold", "crane")
    crane = get_lexicon_spec("de", "crane")
    assert crane.default_priority is None
    assert crane.phoneme_encoding == "ipa"
    assert normalize_lexicon_selection("de", None) == ("gold",)
    assert normalize_lexicon_selection("de", "crane") == ("crane",)


def test_registry_tier_metadata() -> None:
    assert get_lexicon_spec("en-us", "silver").rating == 3


def test_unknown_name_lists_valid_names() -> None:
    try:
        get_lexicon_spec("en-us", "missing")
    except ValueError as exc:
        assert "gold" in str(exc) and "silver" in str(exc)
    else:
        raise AssertionError("unknown lexicon was accepted")
