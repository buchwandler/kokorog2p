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


def test_cached_g2p_survives_cache_clear() -> None:
    clear_cache()
    g2p = get_g2p("en-us", lexicons="gold", use_spacy=False, use_espeak_fallback=False)
    before = g2p.lookup("the")
    clear_cache(deep=True)
    assert g2p.lookup("the") == before
    g2p.close()
    gc.collect()
