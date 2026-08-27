from pathlib import Path

from experiments.de_lexicon_compression.lexlab.sources import load_manifest


def test_manifest_pins_all_sources():
    specs = load_manifest(Path(__file__).parents[1] / "source_manifest.toml")
    assert set(specs) == {"builtin", "gruut_espeak", "crane_wiktionary"}
    assert specs["crane_wiktionary"].revision.startswith("bfd516")
