from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo


def test_runtime_unique_preserves_first_order():
    source = ParsedLexicon.from_pairs(
        SourceInfo("x"), [("weg", "a"), ("weg", "b"), ("weg", "a")]
    )
    assert source.lookup_all("weg") == ("a", "b", "a")
    assert source.runtime_unique().lookup_all("weg") == ("a", "b")
