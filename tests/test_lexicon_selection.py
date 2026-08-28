from kokorog2p import clear_cache, get_g2p


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


def test_explicit_selection_rejects_contradictory_flags() -> None:
    try:
        get_g2p(
            "en-us",
            lexicons="gold",
            load_gold=False,
            use_spacy=False,
            use_espeak_fallback=False,
        )
    except ValueError as exc:
        assert "contradicts" in str(exc)
    else:
        raise AssertionError("contradictory selection was accepted")
