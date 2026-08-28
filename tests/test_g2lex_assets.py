import json
from importlib.resources import files
from pathlib import Path

import g2lex


def test_all_packaged_assets_open_and_match_lock() -> None:
    lock = json.loads(Path("lexicons/lock.json").read_text(encoding="utf-8"))
    for identifier, metadata in lock["assets"].items():
        name = metadata["asset_sha256"]
        assert len(name) == 64
        resource_name = {
            "en-us:gold": "en_us_gold.g2lex",
            "en-us:silver": "en_us_silver.g2lex",
            "en-gb:gold": "en_gb_gold.g2lex",
            "en-gb:silver": "en_gb_silver.g2lex",
            "de-de:gold": "de_gold.g2lex",
            "fr-fr:gold": "fr_gold.g2lex",
            "ja-jp:words": "ja_words.g2lex",
        }[identifier]
        resource = files("kokorog2p.lexicons.data").joinpath(resource_name)
        assert resource.is_file()
        lexicon = g2lex.open_traversable(resource)
        try:
            assert len(lexicon) == metadata["entry_count"]
            assert lexicon.metadata["logical_sha256"] == metadata["logical_sha256"]
        finally:
            lexicon.close()
