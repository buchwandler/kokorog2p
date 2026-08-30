from __future__ import annotations

from types import SimpleNamespace

import g2lex

from benchmarks.benchmark_de_lexicon_sources import score_source
from benchmarks.lexicon_quality.de import to_kokoro_view


def test_kokoro_view_remains_consumer_only() -> None:
    assert to_kokoro_view("crane_wiktionary", "aɪ̯ b") == "I b"
    assert to_kokoro_view("gruut_espeak", "a b") == "ab"
    assert to_kokoro_view("other", "a b") == "a b"


def test_quality_benchmark_consumes_typed_g2lex_source() -> None:
    source = g2lex.TypedLexiconData(
        {"Haus": ("h aʊ̯ s",), "other": ("o",)},
        g2lex.SourceInfo("crane_wiktionary"),
        physical_rows=2,
    )
    entry = SimpleNamespace(word="Haus", expected_raw_ipa="h aʊ̯ s")
    result = score_source(
        source,
        [entry],
        {"h": 1, "W": 2, "s": 3},
        lambda raw, **_: "h W s",
        source_name="crane_wiktionary",
    )
    assert result["coverage"] == 1.0
    assert result["selected_exact_match_rate"] == 1.0
    assert result["rows"][0]["selected_exact"] is True
