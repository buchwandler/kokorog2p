from experiments.de_lexicon_compression.lexlab.compressor import compress_lexicon
from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo


def test_two_part_exact_composition():
    source = ParsedLexicon.from_pairs(
        SourceInfo("toy"), [("1", "a"), ("2", "b"), ("12", "ab")]
    )
    result = compress_lexicon(source, mode="exact-two-part")
    assert result.compressed.lookup_all("12") == ("ab",)
    assert "12" in result.compressed.derived
    assert not result.compressed.verify_against(source)


def test_multipart_and_variant_composition():
    source = ParsedLexicon.from_pairs(
        SourceInfo("toy"),
        [
            ("A", "x"),
            ("A", "q"),
            ("B", "y"),
            ("C", "z"),
            ("ABC", "xyz"),
            ("ABC", "qyz"),
        ],
    )
    result = compress_lexicon(source, mode="exact-multipart")
    assert result.compressed.lookup_all("ABC") == ("xyz", "qyz")
    assert not result.compressed.verify_against(source)


def test_stress_mismatch_is_retained():
    source = ParsedLexicon.from_pairs(
        SourceInfo("toy"),
        [("Haus", "hˈaʊs"), ("Tür", "tˈyːɐ"), ("Haustür", "hˈaʊstˌyːɐ")],
    )
    result = compress_lexicon(source, mode="exact-two-part")
    assert "Haustür" in result.compressed.exceptions
