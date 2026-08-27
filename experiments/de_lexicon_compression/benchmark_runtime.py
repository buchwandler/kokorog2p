#!/usr/bin/env python3
"""Measure isolated decoder load, memory, throughput, and latency."""

from __future__ import annotations

import argparse
import json
import random
import resource
import subprocess
import sys
import time
from pathlib import Path

try:
    from .lexlab.reports import write_json
    from .lexlab.serializer import load_asset
except ImportError:  # direct script execution
    from lexlab.reports import write_json
    from lexlab.serializer import load_asset


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def _worker(run: Path, seed: int, iterations: int) -> dict[str, object]:
    before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    started = time.perf_counter()
    asset = load_asset(run / "compressed.asset" if run.is_dir() else run)
    load_seconds = time.perf_counter() - started
    after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rng = random.Random(seed)
    direct = sorted(asset.atoms)
    derived = sorted(asset.derived)
    misses = [f"__missing_{index}__" for index in range(max(1, min(iterations, 1000)))]

    def measure(words):
        latencies = []
        started = time.perf_counter()
        for _index in range(iterations):
            word = words[rng.randrange(len(words))]
            one = time.perf_counter()
            asset.lookup_all(word)
            latencies.append((time.perf_counter() - one) * 1000)
        elapsed = time.perf_counter() - started
        return {
            "count": iterations,
            "words_per_second": iterations / elapsed if elapsed else 0.0,
            "p50_ms": _percentile(latencies, 0.50),
            "p95_ms": _percentile(latencies, 0.95),
            "p99_ms": _percentile(latencies, 0.99),
        }

    result = {
        "asset_bytes": (run / "compressed.asset" if run.is_dir() else run)
        .stat()
        .st_size,
        "cold_load_ms": load_seconds * 1000,
        "rss_before_kib": before,
        "rss_after_kib": after,
        "peak_rss_kib": after,
        "direct": measure(direct or ["__none__"]),
        "derived": measure(derived or ["__none__"]),
        "misses": measure(misses),
        "composition_cache": {
            "hits": 0,
            "misses": len(derived),
            "note": "decoder has no implicit cache",
        },
    }
    return result


def run_benchmark(
    run: Path, *, output: Path, seed: int = 1729, iterations: int = 10_000
) -> dict[str, object]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        str(run),
        "--seed",
        str(seed),
        "--iterations",
        str(iterations),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    result = json.loads(completed.stdout)
    write_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        print(
            json.dumps(
                _worker(args.run, args.seed, args.iterations),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.output is None:
        parser.error("--output is required outside --worker")
    run_benchmark(
        args.run, output=args.output, seed=args.seed, iterations=args.iterations
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
