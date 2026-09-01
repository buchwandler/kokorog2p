from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.de_crane_transform import (
    CraneRow,
    group_lowercase,
    normalize_key,
    serialize_entries,
    transform_crane,
)


class FakeLexHint:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool]] = []

    def entries(self, word: str, *, all_case_variants: bool = False):
        self.calls.append((word, all_case_variants))
        return (
            SimpleNamespace(
                word="die",
                pos="det",
                pronunciations=(SimpleNamespace(ipa="[diː]"),),
            ),
            SimpleNamespace(
                word="die",
                pos="pron",
                pronunciations=(SimpleNamespace(ipa="diː"),),
            ),
            SimpleNamespace(
                word="Die",
                pos="noun",
                pronunciations=(SimpleNamespace(ipa="/daɪ/"),),
            ),
        )


def test_normalize_key_uses_nfc_lower_without_casefold() -> None:
    assert normalize_key("Die") == "die"
    assert normalize_key("Straße") == "straße"


def test_group_lowercase_preserves_order_and_deduplicates_exact_rows() -> None:
    groups = group_lowercase(
        [
            CraneRow("Die", "daɪ", 0),
            CraneRow("die", "diː", 1),
            CraneRow("die", "diː", 2),
        ]
    )
    assert list(groups) == ["die"]
    assert [(row.source_spelling, row.pronunciation) for row in groups["die"].rows] == [
        ("Die", "daɪ"),
        ("die", "diː"),
    ]


def test_transform_crane_resolves_die_and_queries_all_case_variants(
    tmp_path: Path,
) -> None:
    source = tmp_path / "crane.tsv"
    source.write_text("die\tdiː\nDie\tdaɪ\nHaus\thaʊ̯s\nhaus\thaʊ̯s\n", encoding="utf-8")
    lexhint = FakeLexHint()

    result = transform_crane(source, lexhint_lexicon=lexhint)

    assert result.entries["die"] == {"DEFAULT": "diː", "DET": "diː", "PRON": "diː"}
    assert "Die" not in result.entries
    assert result.entries["haus"] == "haʊ̯s"
    assert lexhint.calls == [("die", True), ("haus", True)]
    assert result.report["groups"][0]["key"] == "die"
    assert result.report["groups"][0]["dropped"] == [
        {"selector": "NOUN", "pronunciation": "daɪ"}
    ]


def test_transform_serialization_is_deterministic() -> None:
    entries = {"z": "z", "die": {"PRON": "diː", "DEFAULT": "diː", "DET": "diː"}}
    assert (
        serialize_entries(entries)
        == '{"die":{"DEFAULT":"diː","DET":"diː","PRON":"diː"},"z":"z"}\n'
    )
