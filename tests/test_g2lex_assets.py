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
