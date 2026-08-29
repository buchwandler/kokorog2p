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
            assert len(lexicon) == metadata["entry_count"]
            assert lexicon.metadata["logical_sha256"] == metadata["logical_sha256"]
        finally:
            lexicon.close()
