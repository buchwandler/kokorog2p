from pathlib import Path

from kokorog2p.lexicons.runtime import validate_runtime_parity
from scripts.build_g2lex_assets import load_manifest


def test_every_canonical_entry_round_trips_through_runtime_layers() -> None:
    results = validate_runtime_parity(load_manifest(), Path("."))
    assert len(results) == 7
    assert all(result["ok"] for result in results), results
