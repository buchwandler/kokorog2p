#!/usr/bin/env python3
"""Compare the supported Japanese G2P backends.

This benchmark measures coverage and throughput. It does not call coverage or
successful conversion "accuracy" because those metrics are not pronunciation
quality measurements.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConfigBenchmark:
    """Results from benchmarking one Japanese backend configuration."""

    config_name: str
    coverage_rate: float
    sentences_per_second: float
    total_time_ms: float
    total_sentences: int
    total_words: int
    successful: int
    failed: int
    unique_phonemes: int
    dependency_metadata: dict[str, str | None]
    errors: list[tuple[int, str, str]] = field(default_factory=list)


def load_synthetic_data() -> dict[str, Any]:
    """Load the checked-in Japanese synthetic benchmark dataset."""
    filepath = Path(__file__).parent / "data" / "ja_synthetic.json"
    if not filepath.is_file():
        raise FileNotFoundError(f"Japanese synthetic data not found: {filepath}")
    with filepath.open(encoding="utf-8") as file:
        return json.load(file)


def _distribution_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def dependency_metadata(backend: str) -> dict[str, str | None]:
    """Return package and runtime identity needed to interpret results."""
    metadata = {
        "kokorog2p": _distribution_version("kokorog2p"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "backend": backend,
        "pyopenjtalk": _distribution_version("pyopenjtalk"),
        "pyopenjtalk-plus": _distribution_version("pyopenjtalk-plus"),
    }
    if backend == "cutlet":
        metadata.update(
            {
                "fugashi": _distribution_version("fugashi"),
                "unidic": _distribution_version("unidic"),
                "unidic-lite": _distribution_version("unidic-lite"),
                "cutlet-implementation": "kokorog2p.vendored.cutlet",
            }
        )
    return metadata


def create_g2p(config: dict[str, Any]):
    """Create a Japanese G2P instance from a backend-only configuration."""
    from kokorog2p.ja import JapaneseG2P

    return JapaneseG2P(backend=config.get("backend", "pyopenjtalk"))


def benchmark_config(
    g2p, data: dict[str, Any], config_name: str, backend: str
) -> ConfigBenchmark:
    """Measure warm steady-state conversion and dataset coverage."""
    sentences = data["sentences"]
    if sentences:
        g2p(sentences[0]["text"])

    successful = 0
    failed = 0
    total_words = 0
    errors: list[tuple[int, str, str]] = []
    phonemes_used: set[str] = set()
    start_time = time.perf_counter()

    for sentence in sentences:
        sentence_id = sentence["id"]
        text = sentence["text"]
        expected_phonemes = sentence["phonemes"]
        total_words += sentence.get("word_count", len(text.split()))
        try:
            tokens = g2p(text)
            got_phonemes = " ".join(
                token.phonemes for token in tokens if token.phonemes
            )
            phonemes_used.update(char for char in got_phonemes if char != " ")
        except Exception as exc:
            got_phonemes = f"ERROR: {exc}"

        expected_normalized = " ".join(expected_phonemes.split())
        got_normalized = " ".join(got_phonemes.split())
        if "ERROR:" not in got_phonemes and expected_normalized == got_normalized:
            successful += 1
        else:
            failed += 1
            if len(errors) < 20:
                errors.append((sentence_id, expected_phonemes, got_phonemes))

    total_time_ms = (time.perf_counter() - start_time) * 1000
    sentence_count = len(sentences)
    return ConfigBenchmark(
        config_name=config_name,
        coverage_rate=(successful / sentence_count * 100) if sentence_count else 0,
        sentences_per_second=(sentence_count / (total_time_ms / 1000))
        if total_time_ms > 0
        else 0,
        total_time_ms=total_time_ms,
        total_sentences=sentence_count,
        total_words=total_words,
        successful=successful,
        failed=failed,
        unique_phonemes=len(phonemes_used),
        dependency_metadata=dependency_metadata(backend),
        errors=errors,
    )


def print_results(results: list[ConfigBenchmark], verbose: bool = False) -> None:
    """Print benchmark results without implying pronunciation accuracy."""
    print("\n" + "=" * 80)
    print("Japanese G2P Backend Comparison")
    print("=" * 80)
    print(
        f"Dataset: {results[0].total_sentences} sentences, "
        f"{results[0].total_words} words"
    )
    print()
    print(f"{'Configuration':<24} {'Coverage':>10} {'Speed':>15} {'Phonemes':>10}")
    print("-" * 80)
    for result in sorted(
        results, key=lambda item: (-item.coverage_rate, -item.sentences_per_second)
    ):
        print(
            f"{result.config_name:<24} {result.coverage_rate:>9.1f}% "
            f"{result.sentences_per_second:>10,.0f} sent/s {result.unique_phonemes:>10}"
        )
        if verbose:
            for sentence_id, expected, got in result.errors[:5]:
                print(
                    f"  Sentence #{sentence_id}: "
                    f"expected={expected[:100]!r} got={got[:100]!r}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Japanese G2P backends")
    parser.add_argument("--output", "-o", type=Path, help="Save results to JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show mismatches")
    parser.add_argument("--config", "-c", choices=["pyopenjtalk", "cutlet"])
    args = parser.parse_args()

    data = load_synthetic_data()
    configurations = {
        "pyopenjtalk": {"backend": "pyopenjtalk"},
        "cutlet": {"backend": "cutlet"},
    }
    if args.config:
        configurations = {args.config: configurations[args.config]}

    results = []
    for name, config in configurations.items():
        print(f"Testing {name}...")
        try:
            result = benchmark_config(create_g2p(config), data, name, config["backend"])
        except Exception as exc:
            print(f"  Backend unavailable: {exc}")
            continue
        results.append(result)

    if not results:
        print("No backend completed successfully", file=sys.stderr)
        return 1

    print_results(results, args.verbose)
    if args.output:
        payload = {
            "dataset": "benchmarks/data/ja_synthetic.json",
            "total_sentences": data["metadata"]["total_sentences"],
            "results": [asdict(result) for result in results],
        }
        args.output.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Results saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
