import inspect

import pytest

import kokorog2p
from kokorog2p.lexicons import normalize_lexicon_selection


def test_public_signatures_use_named_lexicons_only() -> None:
    functions = (
        kokorog2p.get_g2p,
        kokorog2p.phonemize,
        kokorog2p.phonemize_prepared,
    )
    for function in functions:
        parameters = inspect.signature(function).parameters
        legacy_names = {
            "load" + "_gold",
            "load" + "_silver",
            "use" + "_gold",
            "use" + "_silver",
        }
        assert not legacy_names & set(parameters)


def test_no_lexicon_mode_constructs_without_external_data() -> None:
    kokorog2p.clear_cache(deep=True)
    g2p = kokorog2p.get_g2p(
        "en-us",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    assert g2p.lexicon.lexicons == ()
    assert g2p("unlistedword")[0].phonemes == "❓"


def test_invalid_english_selection_is_rejected() -> None:
    with pytest.raises(ValueError, match="Available lexicons: gold"):
        normalize_lexicon_selection("en-gb", ("gold", "silver"))
