#!/usr/bin/env python3
"""Measure fresh-process load cost for baseline and candidate assets."""

from __future__ import annotations

import argparse
import json
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def rss_bytes() -> int:
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(value if platform.system() == "Darwin" else value * 1024)


def _worker(
    kind: str, run: Path, source: str, data_root: Path | None, path: Path | None
) -> None:
    before = rss_bytes()
    started = time.perf_counter()
    if kind == "candidate":
        from .lexreduce.serializer import load_asset

        load_asset(run / "candidate.asset")
    else:
        from experiments.de_lexicon_compression.lexlab.sources import load_source

        load_source(source, data_root=data_root, path=path).runtime_unique()
    elapsed = (time.perf_counter() - started) * 1000
    print(
        json.dumps({"rss_delta_bytes": rss_bytes() - before, "cold_load_ms": elapsed})
    )


def benchmark(
    run: Path,
    *,
    source: str = "builtin",
    data_root: Path | None = None,
    path: Path | None = None,
) -> dict[str, object]:
    values: dict[str, object] = {}
    for kind in ("baseline", "candidate"):
        command = [
            sys.executable,
            "-m",
            "experiments.de_lexicon_entry_reduction.benchmark_memory",
            "--worker",
            kind,
            "--run",
            str(run),
            "--source",
            source,
        ]
        if data_root:
            command.extend(("--data-root", str(data_root)))
        if path:
            command.extend(("--path", str(path)))
        completed = subprocess.run(command, check=True, capture_output=True, text=True)
        values[kind] = json.loads(completed.stdout)
    baseline = values["baseline"]
    candidate = values["candidate"]
    assert isinstance(baseline, dict) and isinstance(candidate, dict)
    baseline_rss = int(baseline["rss_delta_bytes"])
    candidate_rss = int(candidate["rss_delta_bytes"])
    result = {
        "baseline_rss_delta_bytes": baseline_rss,
        "candidate_rss_delta_bytes": candidate_rss,
        "rss_saved_bytes": baseline_rss - candidate_rss,
        "rss_reduction_rate": (baseline_rss - candidate_rss) / baseline_rss
        if baseline_rss
        else 0.0,
        "baseline_cold_load_ms": baseline["cold_load_ms"],
        "candidate_cold_load_ms": candidate["cold_load_ms"],
        "literal_lookup_words_per_second": None,
        "generated_lookup_words_per_second": None,
        "miss_lookup_words_per_second": None,
        "generated_lookup_p50_ms": None,
        "generated_lookup_p95_ms": None,
        "generated_lookup_p99_ms": None,
    }
    result.update(_lookup_metrics(run))
    return result


def _lookup_metrics(run: Path) -> dict[str, object]:
    from experiments.de_lexicon_entry_reduction.lexreduce.serializer import load_asset
    from experiments.de_lexicon_entry_reduction.verify import adversarial_misses

    candidate = load_asset(run / "candidate.asset")
    all_words = candidate.membership.iter_words()
    literal_words = set(candidate.literals)
    generated = tuple(word for word in all_words if word not in literal_words)
    misses = adversarial_misses(all_words)
    metrics: dict[str, object] = {}
    for name, words in (
        ("literal", tuple(candidate.literals)),
        ("generated", generated),
        ("miss", misses),
    ):
        sample = words[:1000]
        started = time.perf_counter()
        durations: list[float] = []
        for word in sample:
            lookup_started = time.perf_counter_ns()
            candidate.lookup_all(word)
            durations.append((time.perf_counter_ns() - lookup_started) / 1_000_000)
        elapsed = time.perf_counter() - started
        metrics[f"{name}_lookup_words_per_second"] = (
            len(sample) / elapsed if elapsed else 0.0
        )
        if name == "generated" and durations:
            ordered = sorted(durations)
            metrics["generated_lookup_p50_ms"] = ordered[len(ordered) * 50 // 100]
            metrics["generated_lookup_p95_ms"] = ordered[len(ordered) * 95 // 100]
            metrics["generated_lookup_p99_ms"] = ordered[len(ordered) * 99 // 100]
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--source", default="builtin")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worker", choices=("baseline", "candidate"))
    args = parser.parse_args()
    if args.worker:
        _worker(args.worker, args.run, args.source, args.data_root, args.path)
        return 0
    result = benchmark(
        args.run, source=args.source, data_root=args.data_root, path=args.path
    )
    destination = args.output or args.run / "runtime.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
