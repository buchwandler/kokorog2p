from experiments.de_lexicon_compression.lexlab.cascade import (
    cross_source_sharing,
    score_cascade,
)
from experiments.de_lexicon_compression.lexlab.compact import (
    deserialize_compact,
    serialize_compact,
    verify_lookup,
)
from experiments.de_lexicon_compression.lexlab.composition import (
    CompositionMetrics,
    exact_composition,
)
from experiments.de_lexicon_compression.lexlab.compressor import compress_lexicon
from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo
from experiments.de_lexicon_compression.lexlab.p4 import (
    front_decode,
    front_encode,
    serialize_front_coded,
)


def test_exact_search_beats_spelling_rank_and_reuses_trie():
    source = ParsedLexicon.from_pairs(
        SourceInfo("toy"),
        [("A", "x"), ("AB", "u"), ("BC", "y"), ("C", "v"), ("ABC", "xy")],
    )
    result = compress_lexicon(source, mode="exact-two-part")
    assert result.compressed.derived["ABC"] == ("A", "BC")
    assert result.metrics.trie_builds == 1


def test_variant_product_is_pruned_before_materialization():
    metrics = CompositionMetrics()
    segmentation, candidate = exact_composition(
        "AB",
        ("xy",),
        {"A": ("x", "x2"), "B": ("y", "y2")},
        mode="exact-two-part",
        max_variant_product=1,
        metrics=metrics,
    )
    assert segmentation is None
    assert candidate == ()
    assert metrics.variant_product_rejections == 1


def test_v2_assets_and_front_coding_round_trip():
    source = ParsedLexicon.from_pairs(
        SourceInfo("toy"), [("a", "x"), ("b", "y"), ("ab", "xy")]
    )
    compressed = compress_lexicon(source).compressed
    for mode in ("exact-multipart-ids", "ipa-intern", "ipa-repair-macros"):
        decoded = deserialize_compact(serialize_compact(compressed, mode))
        assert verify_lookup(decoded, source)["failures"] == 0
    front = deserialize_compact(serialize_front_coded(compressed))
    assert verify_lookup(front, source)["failures"] == 0
    words = ("a", "ab", "abc", "abd")
    assert front_decode(front_encode(words)) == words


def test_cascade_precedence_conflict_and_sharing():
    first = ParsedLexicon.from_pairs(SourceInfo("first"), [("x", "one")])
    second = ParsedLexicon.from_pairs(
        SourceInfo("second"), [("x", "two"), ("y", "why")]
    )
    result = score_cascade([first, second], [("x", ("one",)), ("y", ("why",))])
    assert result["incremental_hits_by_source"] == {"first": 1, "second": 1}
    assert result["conflict_wins_by_source"] == {"first": 1}
    assert (
        cross_source_sharing([first, second])["identical_spelling_shared_variant"]
        == 0
    )
