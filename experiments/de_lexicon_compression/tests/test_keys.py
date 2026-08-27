from experiments.de_lexicon_compression.lexlab.keys import (
    casing_collisions,
    unicode_statistics,
)
from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo


def test_case_collisions_are_separate():
    source = ParsedLexicon.from_pairs(SourceInfo("x"), [("Haus", "a"), ("haus", "b")])
    collisions = casing_collisions(source)
    assert collisions["exact"] == {}
    assert collisions["lower"]["haus"] == ("Haus", "haus")
    assert collisions["casefold"]["haus"] == ("Haus", "haus")


def test_unicode_stats_do_not_collapse_raw_words():
    source = ParsedLexicon.from_pairs(SourceInfo("x"), [("nfd", "é"), ("nfc", "é")])
    assert unicode_statistics(source)["non_nfc_ipa_rows"] == 1
