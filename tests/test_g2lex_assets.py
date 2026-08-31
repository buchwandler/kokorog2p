import hashlib
import json
from importlib.resources import files
from pathlib import Path

import g2lex

from kokorog2p.lexicons.registry import iter_lexicon_specs


def test_all_packaged_assets_open_and_match_lock() -> None:
    lock = json.loads(Path("lexicons/lock.json").read_text(encoding="utf-8"))
    specs = {spec.id: spec for spec in iter_lexicon_specs()}
    assert set(lock["assets"]) == set(specs)
    for identifier, metadata in lock["assets"].items():
        name = metadata["asset_sha256"]
        assert len(name) == 64
        resource = files("kokorog2p.lexicons.data").joinpath(specs[identifier].resource)
        assert resource.is_file()
        lexicon = g2lex.open_traversable(resource)
        try:
            embedded_path = lexicon.metadata.get("source", {}).get("path")
            if embedded_path:
                assert "/" not in embedded_path
                assert "\\" not in embedded_path
            assert len(lexicon) == metadata["entry_count"]
            assert lexicon.metadata["logical_sha256"] == metadata["logical_sha256"]
        finally:
            lexicon.close()


def test_crane_source_hash_and_ordered_variants_are_preserved() -> None:
    source = Path("lexicons/sources/de/crane_wiktionary.tsv")
    lock = json.loads(Path("lexicons/lock.json").read_text(encoding="utf-8"))
    metadata = lock["assets"]["de-de:crane"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata["source_sha256"]
    parsed = g2lex.read_typed_lexicon(source, format="tsv", source_id="de-de:crane")
    asset = g2lex.open("kokorog2p/lexicons/data/de_crane.g2lex")
    try:
        assert asset.get("A") == ("aː", "aːs")
        assert asset.get("0,2-Liter-Flasche") == parsed.entries["0,2-Liter-Flasche"]
        assert asset.metadata["logical_sha256"] == parsed.logical_sha256
    finally:
        asset.close()
