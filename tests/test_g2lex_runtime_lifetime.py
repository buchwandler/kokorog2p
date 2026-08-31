import gc

import pytest

from kokorog2p import clear_cache, get_g2p
from kokorog2p.lexicons.runtime import open_selected


def test_selected_lexicons_close_is_idempotent() -> None:
    selected = open_selected("en-us", ("gold",))
    assert selected.get_hit("the") is not None
    selected.close()
    selected.close()

    with pytest.raises(ValueError):
        selected.get_hit_candidates(("the",))


def test_closing_one_variant_does_not_close_shared_english_assets() -> None:
    clear_cache(deep=True)

    first = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        phoneme_quotes="curly",
    )
    second = get_g2p(
        "en-us",
        use_spacy=False,
        use_espeak_fallback=False,
        phoneme_quotes="ascii",
    )

    assert first is not second
    assert first.lexicon.golds is second.lexicon.golds
    assert first.lexicon.silvers is second.lexicon.silvers

    before = second.lookup("the")
    first.close()
    assert second.lookup("the") == before

    second.close()
    clear_cache(deep=True)
    from kokorog2p.lexicons.runtime import resource_cache_info

    assert resource_cache_info().currsize == 0


def test_cached_g2p_survives_cache_clear() -> None:
    clear_cache()
    g2p = get_g2p("en-us", lexicons="gold", use_spacy=False, use_espeak_fallback=False)
    before = g2p.lookup("the")
    clear_cache(deep=True)
    assert g2p.lookup("the") == before
    g2p.close()
    gc.collect()


def test_shared_german_third_party_resources_survive_close_and_clear() -> None:
    clear_cache(deep=True)
    first = open_selected("de", ("espeak", "olaph"))
    second = open_selected("de", ("espeak", "olaph"))
    try:
        assert first.get_hit("Haus") is not None
        assert second.get_hit("Haus") is not None
        first.close()
        assert second.get_hit("Haus") is not None
        clear_cache(deep=True)
        assert second.get_hit("Haus") is not None
    finally:
        second.close()
        clear_cache(deep=True)
