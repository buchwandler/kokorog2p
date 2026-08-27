from pathlib import Path

from experiments.de_lexicon_compression.lexlab.compressor import compress_lexicon
from experiments.de_lexicon_compression.lexlab.model import ParsedLexicon, SourceInfo
from experiments.de_lexicon_compression.lexlab.serializer import write_asset


def test_runtime_worker_reports_metrics(tmp_path: Path):
    source = ParsedLexicon.from_pairs(
        SourceInfo("toy"), [("a", "x"), ("b", "y"), ("ab", "xy")]
    )
    run = tmp_path / "run"
    run.mkdir()
    write_asset(run / "compressed.asset", compress_lexicon(source).compressed)
    from experiments.de_lexicon_compression.benchmark_runtime import _worker

    result = _worker(run, 1, 10)
    assert result["asset_bytes"] > 0
    assert "p95_ms" in result["direct"]
