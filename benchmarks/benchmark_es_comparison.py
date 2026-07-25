#!/usr/bin/env python3
"""Comprehensive benchmark for Spanish G2P.

This script tests the kokorog2p Spanish G2P implementation.

It measures:
- Accuracy against ground truth
- Processing speed (sentences/second)
- Phoneme coverage

Usage:
    python benchmarks/benchmark_es_comparison.py
    python benchmarks/benchmark_es_comparison.py --output results.json
    python benchmarks/benchmark_es_comparison.py --verbose
"""

import argparse
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ConfigBenchmark:
    """Results from benchmarking a single configuration."""

    config_name: str
    accuracy_percent: float
    sentences_per_second: float
    total_time_ms: float
    total_sentences: int
    total_words: int
    successful: int
    failed: int
    unique_phonemes: int
    errors: list[tuple[int, str, str]] = field(
        default_factory=list
    )  # (id, expected, got)


def load_synthetic_data() -> dict[str, Any]:
    """Load Spanish synthetic benchmark data."""
    filepath = Path(__file__).parent / "data" / "es_synthetic.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Spanish synthetic data not found: {filepath}")

    with open(filepath) as f:
        return json.load(f)


def create_g2p(config: dict[str, Any]):
    """Create a Spanish G2P instance with the given configuration."""
    from kokorog2p.es import SpanishG2P

    return SpanishG2P(
        mark_stress=config.get("mark_stress", True),
        dialect=config.get("dialect", "es"),
    )


def benchmark_config(g2p, data: dict[str, Any], config_name: str) -> ConfigBenchmark:
    """Benchmark a single G2P configuration."""
    sentences = data["sentences"]
    successful = 0
    failed = 0
    total_words = 0
    errors = []
    phonemes_used = set()

    start_time = time.perf_counter()

    for sentence in sentences:
        sentence_id = sentence["id"]
        text = sentence["text"]
        expected_phonemes = sentence["phonemes"]
        word_count = sentence.get("word_count", len(text.split()))

        # Phonemize
        try:
            got_phonemes = g2p.phonemize(text)
            tokens = g2p(text)
        except Exception as e:
            failed += 1
            errors.append((sentence_id, expected_phonemes, f"ERROR: {e}"))
            continue

        # Track unique phonemes
        for token in tokens:
            if token.phonemes:
                phonemes_used.update(c for c in token.phonemes if c.strip())

        # Compare
        if got_phonemes == expected_phonemes:
            successful += 1
        else:
            failed += 1
            errors.append((sentence_id, expected_phonemes, got_phonemes))

        total_words += word_count

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    # Calculate metrics
    total_sentences = len(sentences)
    accuracy = (successful / total_sentences * 100) if total_sentences > 0 else 0
    sent_per_sec = (total_sentences / total_time_ms * 1000) if total_time_ms > 0 else 0

    return ConfigBenchmark(
        config_name=config_name,
        accuracy_percent=accuracy,
        sentences_per_second=sent_per_sec,
        total_time_ms=total_time_ms,
        total_sentences=total_sentences,
        total_words=total_words,
        successful=successful,
        failed=failed,
        unique_phonemes=len(phonemes_used),
        errors=errors[:10],  # Keep first 10 errors
    )


def print_results(results: list[ConfigBenchmark], verbose: bool = False):
    """Print benchmark results in a formatted table."""
    print("\n" + "=" * 80)
    print("SPANISH G2P BENCHMARK RESULTS")
    print("=" * 80)

    for result in results:
        print(f"\nConfiguration: {result.config_name}")
        print(f"  Accuracy:        {result.accuracy_percent:>6.1f}%")
        print(f"  Speed:           {result.sentences_per_second:>6.0f} sent/s")
        print(f"  Total time:      {result.total_time_ms:>6.0f} ms")
        print(
            f"  Sentences:       {result.successful}/{result.total_sentences} correct"
        )
        print(f"  Phonemes found:  {result.unique_phonemes}")

        if verbose and result.errors:
            print("\n  First errors:")
            for sent_id, expected, got in result.errors[:5]:
                print(f"    Sentence {sent_id}:")
                print(f"      Expected: {expected}")
                print(f"      Got:      {got}")

    print("\n" + "=" * 80)


def save_results(results: list[ConfigBenchmark], output_file: Path):
    """Save benchmark results to JSON file."""
    data = {
        "benchmark": "spanish_g2p",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "configurations": [
            {
                "name": r.config_name,
                "accuracy_percent": r.accuracy_percent,
                "sentences_per_second": r.sentences_per_second,
                "total_time_ms": r.total_time_ms,
                "total_sentences": r.total_sentences,
                "total_words": r.total_words,
                "successful": r.successful,
                "failed": r.failed,
                "unique_phonemes": r.unique_phonemes,
                "sample_errors": [
                    {"id": eid, "expected": exp, "got": got}
                    for eid, exp, got in r.errors
                ],
            }
            for r in results
        ],
    }

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Results saved to: {output_file}")


def main():
    """Run Spanish G2P benchmarks."""
    parser = argparse.ArgumentParser(description="Benchmark Spanish G2P configurations")
    parser.add_argument(
        "--output", type=Path, help="Output file for JSON results (optional)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed error information"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Run only a specific configuration (e.g., 'Spanish G2P')",
    )

    args = parser.parse_args()

    # Load benchmark data
    print("Loading Spanish synthetic benchmark data...")
    data = load_synthetic_data()
    print(f"✓ Loaded {data['metadata']['total_sentences']} sentences")

    # Define configurations to test
    all_configs = [
        {
            "name": "Spanish G2P (Full - European)",
            "params": {"mark_stress": True, "dialect": "es"},
        },
        {
            "name": "Spanish G2P (Latin American)",
            "params": {"mark_stress": True, "dialect": "la"},
        },
        {
            "name": "Spanish G2P (No Stress - European)",
            "params": {"mark_stress": False, "dialect": "es"},
        },
        {
            "name": "Spanish G2P (Minimal - Latin American)",
            "params": {"mark_stress": False, "dialect": "la"},
        },
    ]

    # Filter configs if specific one requested
    if args.config:
        all_configs = [c for c in all_configs if c["name"] == args.config]
        if not all_configs:
            print(f"✗ Configuration '{args.config}' not found")
            return

    results = []

    # Benchmark each configuration
    for config in all_configs:
        print(f"\nBenchmarking: {config['name']}...")
        try:
            g2p = create_g2p(config["params"])
            result = benchmark_config(g2p, data, config["name"])
            results.append(result)
            print(
                f"  ✓ {result.accuracy_percent:.1f}% accuracy, "
                f"{result.sentences_per_second:.0f} sent/s"
            )
        except Exception as e:
            print(f"  ✗ Error: {e}")

    # Print results
    print_results(results, verbose=args.verbose)

    # Save to file if requested
    if args.output:
        save_results(results, args.output)


if __name__ == "__main__":
    main()
