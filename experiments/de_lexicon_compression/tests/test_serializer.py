from pathlib import Path

from experiments.de_lexicon_compression.lexlab.compressor import compress_lexicon
from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo
from experiments.de_lexicon_compression.lexlab.serializer import deserialize, serialize


def test_asset_bytes_are_deterministic_and_reloadable(tmp_path: Path):
    source = ParsedLexicon.from_pairs(
        SourceInfo("toy"), [("a", "x"), ("b", "y"), ("ab", "xy")]
    )
    first = serialize(compress_lexicon(source, mode="exact-multipart").compressed)
    second = serialize(compress_lexicon(source, mode="exact-multipart").compressed)
    assert first == second
    assert not deserialize(first).verify_against(source)
