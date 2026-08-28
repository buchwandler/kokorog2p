#!/usr/bin/env python3
"""Measure isolated decoder/baseline load, memory, throughput, and latency."""

from __future__ import annotations

import argparse
import json
import platform
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


def _rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if platform.system() == "Darwin" else value * 1024)


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]


def _measure(
    lookup,
    words: list[str],
    rng: random.Random,
    iterations: int,
) -> dict[str, object]:
    if not words:
        return {"available": False, "reason": "empty_category"}
    latencies = []
    started = time.perf_counter()
    for _index in range(iterations):
        word = words[rng.randrange(len(words))]
        one = time.perf_counter()
        lookup(word)
        latencies.append((time.perf_counter() - one) * 1000)
    elapsed = time.perf_counter() - started
    return {
        "available": True,
        "count": len(words),
        "iterations": iterations,
        "words_per_second": iterations / elapsed if elapsed else 0.0,
        "p50_ms": _percentile(latencies, 0.50),
        "p95_ms": _percentile(latencies, 0.95),
        "p99_ms": _percentile(latencies, 0.99),
    }


def _load_baseline(path: Path):
    value = json.loads(path.read_text(encoding="utf-8"))
    entries = {word: tuple(values) for word, values in value.get("entries", {}).items()}
    return entries, entries.get


def _worker(
    run: Path,
    seed: int,
    iterations: int,
    baseline: bool = False,
) -> dict[str, object]:
    before = _rss_bytes()
    started = time.perf_counter()
    if baseline:
        path = run / "baseline-canonical.json" if run.is_dir() else run
        entries, getter = _load_baseline(path)
        lookup = lambda word: getter(word, ())
        categories = {"atoms": [], "exceptions": sorted(entries), "derived": []}
        asset_bytes = path.stat().st_size
        representation = "baseline-canonical"
    else:
        asset_path = run / "compressed.asset" if run.is_dir() else run
        asset = load_asset(asset_path)
        lookup = asset.lookup_all
        if hasattr(asset, "atoms"):
            categories = {
                "atoms": sorted(asset.atoms),
                "exceptions": sorted(asset.exceptions),
                "derived": sorted(asset.derived),
            }
        else:
            categories = {
                "atoms": sorted(asset.atom_words),
                "exceptions": sorted(asset.exceptions),
                "derived": sorted(asset.derived),
            }
        asset_bytes = asset_path.stat().st_size
        representation = "compressed"
    load_seconds = time.perf_counter() - started
    after = _rss_bytes()
    rng = random.Random(seed)
    misses = [f"__missing_{index}__" for index in range(max(1, min(iterations, 1000)))]
    categories["misses"] = misses
    mixed = [word for values in categories.values() for word in values]
    if not mixed:
        mixed = misses
    measurements = {
        name: _measure(lookup, words, rng, iterations)
        for name, words in (*categories.items(), ("mixed_uniform", mixed))
    }
    result = {
        "representation": representation,
        "asset_bytes": asset_bytes,
        "cold_load_ms": load_seconds * 1000,
        "rss_before_bytes": before,
        "rss_after_bytes": after,
        "rss_delta_bytes": max(0, after - before),
        "peak_rss_bytes": max(before, after),
        "counts": {name: len(words) for name, words in categories.items()},
        "categories": measurements,
        # Backward-compatible names for the original direct/derived benchmark.
        "direct": measurements["atoms"],
        "derived": measurements["derived"],
        "misses": measurements["misses"],
        "composition_cache": {
            "hits": 0,
            "misses": len(categories["derived"]),
            "note": "decoder has no implicit cache",
        },
    }
    return result


def run_benchmark(
    run: Path,
    *,
    output: Path,
    baseline: Path | None = None,
    seed: int = 1729,
    iterations: int = 10_000,
) -> dict[str, object]:
    script = str(Path(__file__).resolve())

    def invoke(*, baseline_mode: bool) -> dict[str, object]:
        command = [
            sys.executable,
            script,
            "--worker",
            str(baseline if baseline_mode else run),
            "--seed",
            str(seed),
            "--iterations",
            str(iterations),
        ]
        if baseline_mode:
            command.append("--baseline-worker")
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        return json.loads(completed.stdout)

    result = invoke(baseline_mode=False)
    baseline_path = baseline or (
        run / "baseline-canonical.json" if run.is_dir() else None
    )
    if baseline_path is not None and baseline_path.exists():
        baseline_result = invoke(baseline_mode=True)
        result["baseline"] = baseline_result
        result["rss_delta_vs_baseline"] = (
            result["rss_delta_bytes"] - baseline_result["rss_delta_bytes"]
        )
        result["cold_load_ratio"] = (
            result["cold_load_ms"] / baseline_result["cold_load_ms"]
            if baseline_result["cold_load_ms"]
            else None
        )
        for category in ("atoms", "exceptions", "derived"):
            compressed = result["categories"][category]
            base = baseline_result["categories"]["exceptions"]
            result[f"lookup_ratio_{category}"] = (
                compressed["words_per_second"] / base["words_per_second"]
                if compressed.get("available") and base.get("available")
                else None
            )
    write_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--iterations", type=int, default=10_000)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--baseline-worker", action="store_true", dest="baseline_mode")
    args = parser.parse_args()
    if args.worker:
        print(
            json.dumps(
                _worker(args.run, args.seed, args.iterations, args.baseline_mode),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    if args.output is None:
        parser.error("--output is required outside --worker")
    run_benchmark(
        args.run,
        output=args.output,
        baseline=args.baseline,
        seed=args.seed,
        iterations=args.iterations,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
