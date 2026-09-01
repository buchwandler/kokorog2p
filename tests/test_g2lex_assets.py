import hashlib
import json
import unicodedata
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


def test_crane_source_provenance_and_transformed_runtime_contract() -> None:
    source = Path("lexicons/sources/de/crane_wiktionary.tsv")
    lock = json.loads(Path("lexicons/lock.json").read_text(encoding="utf-8"))
    metadata = lock["assets"]["de-de:crane"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == metadata["source_sha256"]
    asset = g2lex.open("kokorog2p/lexicons/data/de_crane.g2lex")
    try:
        assert asset.get("a") is not None
        assert asset.get("A") is None
        assert asset.get("0,2-liter-flasche") is not None
        assert asset.get("0,2-Liter-Flasche") is None
        assert asset.metadata["transform"] == "de-crane-lowercase-lexhint-v1"
        assert asset.metadata["crane_source_sha256"] == metadata["source_sha256"]
        assert dict(asset.get("die").items) == {
            "DEFAULT": "diː",
            "DET": "diː",
            "PRON": "diː",
        }
        assert asset.get("Die") is None
    finally:
        asset.close()


def test_crane_runtime_keys_are_nfc_lowercase() -> None:
    asset = g2lex.open("kokorog2p/lexicons/data/de_crane.g2lex")
    try:
        assert all(key == unicodedata.normalize("NFC", key).lower() for key in asset)
    finally:
        asset.close()


def test_phoneme_inventory_audit_traverses_tagged_selectors(tmp_path: Path) -> None:
    from scripts.audit_lexicon_phoneme_inventory import audit

    source = tmp_path / "tagged.json"
    source.write_text(
        '{"die":{"DEFAULT":"diː","DET":"diː","PRON":"diː"}}\n',
        encoding="utf-8",
    )
    asset = tmp_path / "tagged.g2lex"
    g2lex.pack_file(source, asset, input_format="kokoro-json", source_id="test")
    report = audit(asset, vocabulary=set("diː"))
    assert report["entry_count"] == 1
    assert report["variant_count"] == 3
    assert report["ok"]


def test_cstr_german_sources_match_pins_and_adapter_policy() -> None:
    expected = {
        "de-de:espeak": (
            Path("lexicons/sources/de/espeak_de.tsv"),
            "190b62f1ddcf6616b62214173f05b09804635b170f75b9877eceab20b1624dbf",
            23829981,
        ),
        "de-de:olaph": (
            Path("lexicons/sources/de/olaph_de.txt"),
            "aa70d85ce245c8a8f1db2cc109a0f3da6594eaba5b414a61bcd28f1ccc40ca46",
            41709849,
        ),
    }
    for identifier, (source, source_hash, source_size) in expected.items():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
        assert source.stat().st_size == source_size
        parsed = g2lex.read_typed_lexicon(
            source, format="ipa-tsv", source_id=identifier
        )
        asset = g2lex.open(
            f"kokorog2p/lexicons/data/de_{identifier.rsplit(':', 1)[1]}.g2lex"
        )
        try:
            assert asset.metadata["logical_sha256"] == parsed.logical_sha256
            if identifier.endswith(":espeak"):
                assert asset.get("word") is None
            for value in parsed.entries.values():
                for pronunciation in g2lex.pronunciation_variants(value):
                    assert not (
                        pronunciation.startswith("/") and pronunciation.endswith("/")
                    )
                    break
            if identifier.endswith(":olaph"):
                assert "/" in asset.get("1,6-Liter-Benzinern")[0]
        finally:
            asset.close()
