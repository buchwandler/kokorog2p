import inspect

import kokorog2p
from kokorog2p.fr import FrenchG2P


def test_constructor_has_no_legacy_tier_parameters() -> None:
    legacy = {"load_" + "gold", "load_" + "silver", "use_" + "gold", "use_" + "silver"}
    assert not legacy & set(inspect.signature(FrenchG2P).parameters)


def test_no_lexicon_mode_works_without_external_data() -> None:
    g2p = FrenchG2P(
        language="fr-fr",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    assert g2p.lexicon.lexicons == ()
    assert g2p("motinconnu")[0].phonemes == "?"
    g2p.close()


def test_factory_no_lexicon_mode_for_french() -> None:
    kokorog2p.clear_cache(deep=True)
    g2p = kokorog2p.get_g2p(
        "fr-fr",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    assert g2p.lexicon.lexicons == ()
