#!/usr/bin/env python3
"""Comprehensive benchmark comparison for German G2P configurations.

This script tests all possible configurations of kokorog2p for German:
- Lexicon-only (gold)
- Espeak fallback (with gold/none)
- Goruut fallback (with gold/none)

It measures:
- Accuracy against ground truth
- Processing speed (sentences/second)
- Phoneme coverage

Usage:
    python benchmarks/benchmark_de_comparison.py
    python benchmarks/benchmark_de_comparison.py --output results.json
    python benchmarks/benchmark_de_comparison.py --verbose
    python benchmarks/benchmark_de_comparison.py --config "Gold + Espeak"
"""

import argparse
import json
import sys
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
    """Load German synthetic benchmark data."""
    filepath = Path(__file__).parent / "data" / "de_synthetic.json"
    if not filepath.exists():
        raise FileNotFoundError(f"German synthetic data not found: {filepath}")

    with open(filepath) as f:
        return json.load(f)


def create_g2p(config: dict[str, Any]):
    """Create a German G2P instance with the given configuration."""
    from kokorog2p.de import GermanG2P

    return GermanG2P(
        use_espeak_fallback=config.get("use_espeak", False),
        use_goruut_fallback=config.get("use_goruut", False),
        load_gold=config.get("load_gold", True),
        strip_stress=False,  # Keep stress markers for accurate comparison
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
            tokens = g2p(text)
        except Exception as e:
            failed += 1
            errors.append((sentence_id, expected_phonemes, f"ERROR: {e}"))
            continue

        # Extract phonemes
        all_phonemes = []
        for token in tokens:
            if token.phonemes:
                all_phonemes.append(token.phonemes)
                # Track unique phonemes
                phonemes_used.update(
                    c for c in token.phonemes.split() if c not in ("", " ")
                )

        got_phonemes = " ".join(all_phonemes)
        total_words += word_count

        # Compare (normalize whitespace and stress markers for comparison)
        expected_norm = " ".join(expected_phonemes.split())
        got_norm = " ".join(got_phonemes.split())

        # Also try without stress markers
        expected_no_stress = (
            expected_norm.replace("ˈ", "").replace("ˌ", "").replace("ː", "")
        )
        got_no_stress = got_norm.replace("ˈ", "").replace("ˌ", "").replace("ː", "")

        if expected_norm == got_norm or expected_no_stress == got_no_stress:
            successful += 1
        else:
            failed += 1
            if len(errors) < 20:
                errors.append((sentence_id, expected_phonemes, got_phonemes))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return ConfigBenchmark(
        config_name=config_name,
        accuracy_percent=(successful / len(sentences) * 100) if sentences else 0,
        sentences_per_second=len(sentences) / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        total_time_ms=total_time_ms,
        total_sentences=len(sentences),
        total_words=total_words,
        successful=successful,
        failed=failed,
        unique_phonemes=len(phonemes_used),
        errors=errors,
    )


def print_results(results: list[ConfigBenchmark], verbose: bool = False):
    """Print benchmark results in a nice table."""
    print("\n" + "=" * 80)
    print("German G2P Configuration Comparison")
    print("=" * 80)
    print(
        f"Dataset: {results[0].total_sentences} sentences, "
        f"{results[0].total_words} words"
    )
    print()

    # Table header
    print(f"{'Configuration':<30} {'Accuracy':>10} {'Speed':>15} {'Phonemes':>10}")
    print("-" * 80)

    # Sort by accuracy, then speed
    sorted_results = sorted(
        results, key=lambda x: (-x.accuracy_percent, -x.sentences_per_second)
    )

    for result in sorted_results:
        print(
            f"{result.config_name:<30} "
            f"{result.accuracy_percent:>9.1f}% "
            f"{result.sentences_per_second:>10,.0f} sent/s "
            f"{result.unique_phonemes:>10}"
        )

    # Recommendations
    print("\n" + "=" * 80)
    print("Recommendations:")
    print("=" * 80)

    best_accuracy = max(results, key=lambda x: x.accuracy_percent)
    best_speed = max(results, key=lambda x: x.sentences_per_second)

    print(
        f"Best accuracy:  {best_accuracy.config_name} "
        f"({best_accuracy.accuracy_percent:.1f}%)"
    )
    print(
        f"Fastest:        {best_speed.config_name} "
        f"({best_speed.sentences_per_second:,.0f} sent/s)"
    )
    print()

    # Show errors if verbose
    if verbose:
        for result in sorted_results:
            if result.errors:
                print(f"\n--- Errors for {result.config_name} ---")
                for sentence_id, expected, got in result.errors[:5]:
                    print(f"Sentence #{sentence_id}:")
                    print(f"  Expected: {expected[:100]}")
                    print(f"  Got:      {got[:100]}")
                if len(result.errors) > 5:
                    print(f"  ... and {len(result.errors) - 5} more errors")


def main():
    parser = argparse.ArgumentParser(description="Benchmark German G2P configurations")
    parser.add_argument("--output", "-o", type=Path, help="Save results to JSON file")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed errors"
    )
    parser.add_argument(
        "--config", "-c", type=str, help="Test only specific configuration"
    )

    args = parser.parse_args()

    # Load data
    print("Loading German synthetic data...")
    data = load_synthetic_data()
    print(f"Loaded {len(data['sentences'])} sentences")

    # Define configurations to test
    all_configs = {
        "Gold only": {
            "load_gold": True,
            "use_espeak": False,
            "use_goruut": False,
        },
        "Gold + Espeak": {
            "load_gold": True,
            "use_espeak": True,
            "use_goruut": False,
        },
        "Gold + Goruut": {
            "load_gold": True,
            "use_espeak": False,
            "use_goruut": True,
        },
        "Espeak only": {
            "load_gold": False,
            "use_espeak": True,
            "use_goruut": False,
        },
        "Goruut only": {
            "load_gold": False,
            "use_espeak": False,
            "use_goruut": True,
        },
    }

    # Filter if specific config requested
    if args.config:
        if args.config not in all_configs:
            print(f"Error: Unknown configuration '{args.config}'")
            print(f"Available: {', '.join(all_configs.keys())}")
            return 1
        configs_to_test = {args.config: all_configs[args.config]}
    else:
        configs_to_test = all_configs

    # Run benchmarks
    results = []
    for config_name, config in configs_to_test.items():
        print(f"\nTesting: {config_name}...")
        g2p = create_g2p(config)
        result = benchmark_config(g2p, data, config_name)
        results.append(result)
        print(
            f"  → {result.accuracy_percent:.1f}% accuracy, "
            f"{result.sentences_per_second:,.0f} sent/s"
        )

    # Print results
    print_results(results, verbose=args.verbose)

    # Save to JSON if requested
    if args.output:
        output_data = {
            "dataset": "de_synthetic.json",
            "total_sentences": data["metadata"]["total_sentences"],
            "total_words": sum(s.get("word_count", 0) for s in data["sentences"]),
            "results": [
                {
                    "config_name": r.config_name,
                    "accuracy_percent": r.accuracy_percent,
                    "sentences_per_second": r.sentences_per_second,
                    "total_time_ms": r.total_time_ms,
                    "successful": r.successful,
                    "failed": r.failed,
                    "unique_phonemes": r.unique_phonemes,
                }
                for r in results
            ],
        }

        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\n✓ Results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
