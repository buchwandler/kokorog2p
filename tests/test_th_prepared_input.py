from __future__ import annotations

from dataclasses import dataclass

from kokorog2p.th.engine import EngineResult
from kokorog2p.th.g2p import ThaiG2P


@dataclass
class RecordingEngine:
    sources: list[str] | None = None

    def pronounce_thai_chunk(self, source: str) -> EngineResult:
        if self.sources is None:
            self.sources = []
        self.sources.append(source)
        return EngineResult(source=source, raw_ipa="a2")


def test_prepared_thai_input_skips_legacy_semantic_normalizer() -> None:
    engine = RecordingEngine()
    g2p = ThaiG2P(engine=engine, latin_fallback="none")
    g2p._kokorog2p_prepared_input = True

    g2p("สิบสอง นาฬิกา ศูนย์ ห้า นาที")

    assert engine.sources == ["สิบสอง", "นาฬิกา", "ศูนย์", "ห้า", "นาที"]
