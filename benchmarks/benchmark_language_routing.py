"""Focused benchmark for selected-lexicon language routing.

Run with ``python benchmarks/benchmark_language_routing.py --rounds 20``.
The same configured G2P instances are used for evidence routing and normal
phonemization, so routing cost is reported separately from pronunciation cost.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Any

from kokorog2p import get_g2p
from kokorog2p.language_routing import LanguageRoutingConfig, route_languages
from kokorog2p.tokenization import tokenize_with_offsets


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    text: str
    mode: str


CASES = (
    BenchmarkCase("auto-off", "Die Diskussion bleibt unverändert.", "off"),
    BenchmarkCase("auto-all-default", "Die Diskussion bleibt unverändert.", "auto"),
    BenchmarkCase("auto-repeated-foreign", "File File File File", "auto"),
    BenchmarkCase("auto-mixed-compounds", "Manpowerdiskussion wird gecancelt.", "auto"),
)


def run_benchmark(*, rounds: int = 10) -> list[dict[str, Any]]:
    """Measure routing and ordinary phonemization using shared G2P objects."""
    g2ps = {
        "de-de": get_g2p("de", use_spacy=False),
        "en-us": get_g2p("en-us", use_spacy=False),
    }
    try:
        results: list[dict[str, Any]] = []
        for case in CASES:
            tokens = tokenize_with_offsets(case.text, lang="de-de", keep_punct=True)
            config = LanguageRoutingConfig(
                mode=case.mode,
                languages=("de-de", "en-us"),
            )
            for _ in range(2):
                route_languages(
                    case.text,
                    tokens,
                    default_language="de-de",
                    config=config,
                    resolve_g2p=g2ps.__getitem__,
                    target_model="1.0",
                )
                g2ps["de-de"].phonemize(case.text)
            route_start = time.perf_counter()
            for _ in range(rounds):
                route_languages(
                    case.text,
                    tokens,
                    default_language="de-de",
                    config=config,
                    resolve_g2p=g2ps.__getitem__,
                    target_model="1.0",
                )
            routing_ms = (time.perf_counter() - route_start) * 1000 / rounds
            phonemize_start = time.perf_counter()
            for _ in range(rounds):
                g2ps["de-de"].phonemize(case.text)
            phonemization_ms = (time.perf_counter() - phonemize_start) * 1000 / rounds
            results.append(
                {
                    "case": case.name,
                    "rounds": rounds,
                    "routing_ms": routing_ms,
                    "phonemization_ms": phonemization_ms,
                }
            )
        return results
    finally:
        for g2p in g2ps.values():
            g2p.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=10)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    print(json.dumps(run_benchmark(rounds=args.rounds), indent=2))


if __name__ == "__main__":
    main()
