import hashlib
import json
from importlib.resources import files
from pathlib import Path

import g2lex

from kokorog2p.lexicons.registry import iter_lexicon_specs


def test_all_packaged_assets_open_and_match_lock() -> None:
    lock = json.loads(Path("lexicons/lock.json").read_text(encoding="utf-8"))
    packaged_specs = {
        spec.id: spec for spec in iter_lexicon_specs() if spec.resource is not None
    }
    assert set(lock["assets"]) == set(packaged_specs)
    for identifier, metadata in lock["assets"].items():
        name = metadata["asset_sha256"]
        assert len(name) == 64
        resource = files("kokorog2p.lexicons.data").joinpath(
            packaged_specs[identifier].resource
        )
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


def test_swedish_nst_source_and_asset_match_pins() -> None:
    source = Path("lexicons/sources/sv/sv_nst.tsv")
    lock = json.loads(Path("lexicons/lock.json").read_text(encoding="utf-8"))
    metadata = lock["assets"]["sv-se:nst"]

    assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata["source_sha256"]
    assert source.stat().st_size == 38008908

    parsed = g2lex.read_typed_lexicon(source, format="tsv", source_id="sv-se:nst")
    asset = g2lex.open("kokorog2p/lexicons/data/sv_nst.g2lex")
    try:
        assert len(asset) == 812343
        assert len(asset) == metadata["entry_count"]
        assert asset.metadata["logical_sha256"] == metadata["logical_sha256"]
        assert asset.metadata["provider"] == "Joakim/kokoro-sv-g2p"
        assert asset.metadata["revision"] == "d19dd10"
        assert asset.metadata["source"]["source_sha256"] == metadata["source_sha256"]
        assert asset.get("hej") == parsed.entries["hej"]
    finally:
        asset.close()
