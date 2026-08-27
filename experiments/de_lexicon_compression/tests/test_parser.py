from pathlib import Path

import pytest

from experiments.de_lexicon_compression.lexlab.model import SourceInfo
from experiments.de_lexicon_compression.lexlab.parse import (
    LexiconFormatError,
    parse_json_bytes,
    parse_tsv,
    parse_tsv_text,
)

SOURCE = SourceInfo("fixture", format="tsv_variants")


def test_tsv_preserves_order_duplicates_and_spaces(tmp_path: Path):
    path = tmp_path / "source.tsv"
    path.write_text("weg\tvɛk\nweg\tveːk\nweg\tvɛk\nword\t ipa \n", encoding="utf-8")
    parsed = parse_tsv(path, SOURCE)
    assert parsed.lookup_all("weg") == ("vɛk", "veːk", "vɛk")
    assert parsed.lookup_all("word") == (" ipa ",)
    assert parsed.lookup_records("weg")[1].line_number == 2
    assert parsed.metadata["duplicate_identical_rows"] == 1


def test_tsv_requires_exactly_two_columns():
    with pytest.raises(LexiconFormatError):
        parse_tsv_text("word\tipa\textra\n", SOURCE)


def test_json_validation_and_tuple_values():
    parsed = parse_json_bytes(
        b'{"Haus":"ha\\u028as"}', SourceInfo("builtin", format="json_single")
    )
    assert parsed.lookup_all("Haus") == ("haʊs",)
    with pytest.raises(LexiconFormatError):
        parse_json_bytes(b"[]", SourceInfo("builtin", format="json_single"))
