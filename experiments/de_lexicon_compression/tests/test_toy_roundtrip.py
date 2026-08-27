from pathlib import Path

from experiments.de_lexicon_compression.lexlab.compressor import compress_lexicon
from experiments.de_lexicon_compression.lexlab.model import SourceInfo
from experiments.de_lexicon_compression.lexlab.parse import parse_tsv
from experiments.de_lexicon_compression.lexlab.serializer import deserialize, serialize


def test_fixture_roundtrip():
    root = Path(__file__).parents[1] / "fixtures"
    source = parse_tsv(
        root / "toy_variants.tsv", SourceInfo("toy", format="tsv_variants")
    )
    result = compress_lexicon(source, mode="exact-multipart")
    assert not result.compressed.verify_against(source)
    assert not deserialize(serialize(result.compressed)).verify_against(source)
