from kokorog2p.lexicons import available_lexicons, get_lexicon_spec


def test_registry_aliases_and_order() -> None:
    assert available_lexicons("en") == ("gold", "silver")
    assert available_lexicons("english") == ("gold", "silver")
    assert available_lexicons("ja_jp") == ("words",)
    assert get_lexicon_spec("en-us", "gold").rating == 4
    assert get_lexicon_spec("en-us", "silver").rating == 3


def test_unknown_name_lists_valid_names() -> None:
    try:
        get_lexicon_spec("en-us", "missing")
    except ValueError as exc:
        assert "gold" in str(exc) and "silver" in str(exc)
    else:
        raise AssertionError("unknown lexicon was accepted")
