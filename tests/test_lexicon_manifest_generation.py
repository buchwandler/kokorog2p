from pathlib import Path

from kokorog2p.lexicons.registry import iter_lexicon_specs
from scripts.build_g2lex_assets import load_manifest, registry_text


def test_generated_registry_matches_manifest() -> None:
    generated = Path("kokorog2p/lexicons/_generated_registry.py").read_text(
        encoding="utf-8"
    )
    assert generated == registry_text(load_manifest())


def test_manifest_is_complete_registry_source() -> None:
    records = load_manifest()
    specs = iter_lexicon_specs()
    assert [record["id"] for record in records] == [spec.id for spec in specs]
    assert all("default_priority" in record for record in records)
