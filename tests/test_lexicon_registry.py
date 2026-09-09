from kokorog2p.lexicons import (
    available_lexicons,
    get_lexicon_spec,
    normalize_lexicon_selection,
)


def test_consolidated_english_and_french_registry() -> None:
    assert available_lexicons("en-us") == ("gold",)
    assert available_lexicons("en-gb") == ("gold",)
    assert available_lexicons("fr-fr") == ("gold",)
    assert get_lexicon_spec("en-us", "gold").id == "en-us:gold"
    assert get_lexicon_spec("en-gb", "gold").id == "en-gb:gold"
    assert get_lexicon_spec("fr-fr", "gold").id == "fr-fr:gold"


def test_unrelated_external_lexicons_remain_available() -> None:
    assert available_lexicons("de") == ("gold", "crane", "espeak", "olaph", "lexhint")
    assert available_lexicons("ja") == ("lexhint",)
    assert get_lexicon_spec("ru", "lexhint").backend == "lexphon"


def test_defaults_and_explicit_selection() -> None:
    assert normalize_lexicon_selection("en-us", None) == ("gold",)
    assert normalize_lexicon_selection("en-us", "gold") == ("gold",)
    assert normalize_lexicon_selection("en-us", ("gold",)) == ("gold",)
    assert normalize_lexicon_selection("en-us", ()) == ()


def test_silver_is_not_an_english_option() -> None:
    for language in ("en-us", "en-gb"):
        try:
            normalize_lexicon_selection(language, "silver")
        except ValueError as exc:
            assert "Available lexicons: gold" in str(exc)
        else:
            raise AssertionError("silver was accepted")


def test_duplicate_and_unknown_names_fail() -> None:
    try:
        normalize_lexicon_selection("en-us", ("gold", "gold"))
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate selection was accepted")

    try:
        normalize_lexicon_selection("en-us", "missing")
    except ValueError as exc:
        assert "gold" in str(exc)
    else:
        raise AssertionError("unknown selection was accepted")
