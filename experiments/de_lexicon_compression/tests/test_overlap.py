from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo
from experiments.de_lexicon_compression.lexlab.overlap import pair_metrics


def test_overlap_reports_raw_and_variant_agreement():
    left = ParsedLexicon.from_pairs(SourceInfo("left"), [("Haus", "h")])
    right = ParsedLexicon.from_pairs(
        SourceInfo("right"), [("Haus", "h"), ("haus", "x")]
    )
    metrics = pair_metrics(left, right)
    assert metrics["exact_spelling_intersection"] == 1
    assert metrics["exact_raw_pronunciation_agreement"] == 1
    assert metrics["lowercase_spelling_intersection"] == 1
