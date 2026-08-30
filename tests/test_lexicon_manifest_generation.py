from importlib.metadata import version as distribution_version
from pathlib import Path

import pytest

import scripts.build_g2lex_assets as build_assets
from kokorog2p.lexicons.registry import iter_lexicon_specs
from scripts.build_g2lex_assets import load_manifest, registry_text


def test_generated_registry_matches_manifest() -> None:
    generated = Path("kokorog2p/lexicons/_generated_registry.py").read_text(
        encoding="utf-8"
    )
    assert generated == registry_text(load_manifest())


def test_asset_tools_use_distribution_version() -> None:
    assert build_assets.G2LEX_VERSION == distribution_version("g2lex")


def test_manifest_is_complete_registry_source() -> None:
    records = load_manifest()
    specs = iter_lexicon_specs()
    assert [record["id"] for record in records] == [spec.id for spec in specs]
    assert [record.get("default_priority") for record in records] == [
        spec.default_priority for spec in specs
    ]


def test_manifest_allows_opt_in_record_without_default_priority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        """schema_version = 1\n\n"""
        "[[lexicon]]\n"
        'id = "xx-xx:local"\n'
        'language = "xx-xx"\n'
        'name = "local"\n'
        'kind = "pronunciation"\n'
        'source = "sources/words.tsv"\n'
        'source_format = "tsv"\n'
        'asset = "assets/words.g2lex"\n'
        "case_aliases = false\n"
        'phoneme_encoding = "ipa"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(build_assets, "MANIFEST_PATH", manifest)
    assert load_manifest()[0].get("default_priority") is None


def test_manifest_rejects_incomplete_third_party_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        """schema_version = 1\n\n"""
        "[[lexicon]]\n"
        'id = "xx-xx:third"\n'
        'language = "xx-xx"\n'
        'name = "third"\n'
        'kind = "pronunciation"\n'
        'source = "sources/words.tsv"\n'
        'source_format = "tsv"\n'
        'asset = "assets/words.g2lex"\n'
        "case_aliases = false\n"
        'phoneme_encoding = "ipa"\n'
        'provider = "example"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(build_assets, "MANIFEST_PATH", manifest)
    with pytest.raises(ValueError, match="missing provenance"):
        load_manifest()
