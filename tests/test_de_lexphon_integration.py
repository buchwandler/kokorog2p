"""Integration checks for explicitly provisioned German Lexphon data."""

import pytest

from kokorog2p.de import GermanG2P, GermanLexicon


@pytest.mark.integration
def test_all_named_german_lexphon_layers_are_usable() -> None:
    for name in ("gold", "crane", "espeak", "olaph"):
        lexicon = GermanLexicon(lexicons=(name,))
        try:
            assert lexicon.lookup("Haus")
        finally:
            lexicon.close()


@pytest.mark.integration
def test_german_g2p_uses_provisioned_lexphon_data() -> None:
    g2p = GermanG2P(
        lexicons=("gold",),
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )
    try:
        tokens = [token for token in g2p("Haus") if token.is_word]
        assert tokens
        assert tokens[0].phonemes
        assert tokens[0].get("rating") == 5
    finally:
        g2p.close()
