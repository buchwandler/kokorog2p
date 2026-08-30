from kokorog2p import clear_cache, get_g2p, phonemize
from kokorog2p.lexicons import normalize_lexicon_selection


def test_named_selection_and_cache_identity() -> None:
    clear_cache()
    gold = get_g2p("en-us", lexicons="gold", use_spacy=False, use_espeak_fallback=False)
    stack = get_g2p(
        "en-us", lexicons=("gold", "silver"), use_spacy=False, use_espeak_fallback=False
    )
    reverse = get_g2p(
        "en-us", lexicons=("silver", "gold"), use_spacy=False, use_espeak_fallback=False
    )
    assert gold is get_g2p(
        "english", lexicons="gold", use_spacy=False, use_espeak_fallback=False
    )
    assert gold is not stack
    assert stack is not reverse
    assert gold.lexicon.lexicons == ("gold",)
    assert stack.lexicon.lexicons == ("gold", "silver")


def test_legacy_flags_map_to_named_layers() -> None:
    clear_cache()
    for flags, expected in (
        ((True, True), ("gold", "silver")),
        ((True, False), ("gold",)),
        ((False, True), ("silver",)),
        ((False, False), ()),
    ):
        g2p = get_g2p(
            "en-us",
            load_gold=flags[0],
            load_silver=flags[1],
            use_spacy=False,
            use_espeak_fallback=False,
        )
        assert g2p.lexicon.lexicons == expected


def test_explicit_selection_takes_precedence_over_legacy_flags() -> None:
    clear_cache()
    g2p = get_g2p(
        "de",
        lexicons="gold",
        load_gold=False,
        load_silver=True,
        use_spacy=False,
        use_espeak_fallback=False,
    )
    assert g2p.lexicon.lexicons == ("gold",)


def test_german_selection_preserves_explicit_order() -> None:
    assert normalize_lexicon_selection("de", ("gold", "crane")) == ("gold", "crane")
    assert normalize_lexicon_selection("de", ("crane", "gold")) == ("crane", "gold")


def test_german_named_lexicons_have_distinct_cache_identities() -> None:
    clear_cache()
    options = {"use_spacy": False, "use_espeak_fallback": False}
    gold = get_g2p("de", lexicons="gold", **options)
    crane = get_g2p("de", lexicons="crane", **options)
    reverse = get_g2p("de", lexicons=("crane", "gold"), **options)
    assert gold is not crane
    assert crane is not reverse
    assert gold.lexicon.lexicons == ("gold",)
    assert crane.lexicon.lexicons == ("crane",)
    assert reverse.lexicon.lexicons == ("crane", "gold")


def test_phonemize_accepts_german_crane_selection() -> None:
    result = phonemize(
        "Haus",
        language="de",
        lexicons="crane",
        use_espeak_fallback=False,
        use_spacy=False,
        return_ids=False,
    )
    assert result.phonemes == "hWs"
