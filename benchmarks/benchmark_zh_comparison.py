#!/usr/bin/env python3
"""Comprehensive benchmark comparison for Chinese G2P configurations.

This script tests Chinese (Mandarin) G2P with kokorog2p:
- Default (ZHFrontend with Zhuyin notation)
- With espeak fallback (optional)

It measures:
- Accuracy against ground truth
- Processing speed (sentences/second)
- Phoneme coverage (Zhuyin characters)

Usage:
    python benchmarks/benchmark_zh_comparison.py
    python benchmarks/benchmark_zh_comparison.py --output results.json
    python benchmarks/benchmark_zh_comparison.py --verbose
    python benchmarks/benchmark_zh_comparison.py --config "Chinese G2P"
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
    """Load Chinese synthetic benchmark data."""
    filepath = Path(__file__).parent / "data" / "zh_synthetic.json"
    if not filepath.exists():
        raise FileNotFoundError(f"Chinese synthetic data not found: {filepath}")

    with open(filepath) as f:
        return json.load(f)


def create_g2p(config: dict[str, Any]):
    """Create a Chinese G2P instance with the given configuration."""
    from kokorog2p.zh import ChineseG2P

    return ChineseG2P(
        use_espeak_fallback=config.get("use_espeak", False),
        version="1.1",  # Use ZHFrontend with Zhuyin notation
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
        word_count = sentence.get("word_count", len(text.replace(" ", "")))

        # Phonemize
        try:
            tokens = g2p(text)
        except Exception as e:
            failed += 1
            errors.append((sentence_id, expected_phonemes, f"ERROR: {e}"))
            continue

        # Extract phonemes (character-based for Chinese)
        all_phonemes = []
        for token in tokens:
            if token.phonemes:
                all_phonemes.append(token.phonemes)
                # Track unique phonemes (Zhuyin characters)
                phonemes_used.update(c for c in token.phonemes if c not in ("", " "))

        # Chinese uses character-based phonemes (no spaces)
        got_phonemes = "".join(all_phonemes)
        total_words += word_count

        # Compare (exact match for Chinese)
        if expected_phonemes == got_phonemes:
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
    print("Chinese (Mandarin) G2P Configuration Comparison")
    print("=" * 80)
    print(
        f"Dataset: {results[0].total_sentences} sentences, "
        f"{results[0].total_words} characters"
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
        accuracy_str = f"{result.accuracy_percent:.1f}%"
        speed_str = f"{result.sentences_per_second:,.0f} sent/s"
        phonemes_str = f"{result.unique_phonemes}"

        print(
            f"{result.config_name:<30} {accuracy_str:>10} "
            f"{speed_str:>15} {phonemes_str:>10}"
        )

    print()

    # Show errors for configurations with <100% accuracy
    if verbose:
        for result in sorted_results:
            if result.failed > 0:
                print(f"\n{result.config_name} Errors ({len(result.errors)} shown):")
                print("-" * 80)
                for sent_id, expected, got in result.errors[:10]:
                    print(f"Sentence {sent_id}:")
                    print(f"  Expected: {expected}")
                    print(f"  Got:      {got}")
                    print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Benchmark Chinese G2P configurations")
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed error information",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="Run only specific configuration (e.g., 'Chinese G2P')",
    )

    args = parser.parse_args()

    # Load benchmark data
    print("Loading Chinese synthetic benchmark data...")
    data = load_synthetic_data()
    print(f"Loaded {len(data['sentences'])} sentences")

    # Define configurations to test
    configs = [
        {
            "name": "Chinese G2P (ZHFrontend)",
            "use_espeak": False,
        },
        {
            "name": "Chinese G2P + Espeak",
            "use_espeak": True,
        },
    ]

    # Filter by --config if specified
    if args.config:
        configs = [c for c in configs if c["name"] == args.config]
        if not configs:
            print(f"Error: Configuration '{args.config}' not found")
            return 1

    # Run benchmarks
    results = []
    for config in configs:
        print(f"\nBenchmarking: {config['name']}...")
        g2p = create_g2p(config)
        result = benchmark_config(g2p, data, config["name"])
        results.append(result)
        print(
            f"  {result.accuracy_percent:.1f}% accuracy, "
            f"{result.sentences_per_second:,.0f} sent/s"
        )

    # Print results table
    print_results(results, verbose=args.verbose)

    # Recommendation
    print("=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    best = max(results, key=lambda x: (x.accuracy_percent, x.sentences_per_second))
    print(f"Best configuration: {best.config_name}")
    print(f"  Accuracy: {best.accuracy_percent:.1f}%")
    print(f"  Speed: {best.sentences_per_second:,.0f} sentences/second")
    print(f"  Phonemes: {best.unique_phonemes} unique Zhuyin characters")
    print()

    # Notes
    print("NOTES:")
    print("- Chinese uses Zhuyin (Bopomofo) phonetic notation, not IPA")
    print("- Phoneme representation is character-based (like Japanese/Korean)")
    print("- Includes tone markers (1-5) and special Zhuyin characters")
    print("- Tone sandhi and erhua (儿化音) variations are handled automatically")
    print()

    # Save to JSON if requested
    if args.output:
        output_data = {
            "benchmark_type": "chinese_g2p_comparison",
            "dataset": {
                "total_sentences": results[0].total_sentences,
                "total_words": results[0].total_words,
            },
            "results": [
                {
                    "config_name": r.config_name,
                    "accuracy_percent": r.accuracy_percent,
                    "sentences_per_second": r.sentences_per_second,
                    "total_time_ms": r.total_time_ms,
                    "successful": r.successful,
                    "failed": r.failed,
                    "unique_phonemes": r.unique_phonemes,
                    "errors": [
                        {"id": e[0], "expected": e[1], "got": e[2]} for e in r.errors
                    ],
                }
                for r in results
            ],
            "recommendation": {
                "config_name": best.config_name,
                "accuracy_percent": best.accuracy_percent,
                "sentences_per_second": best.sentences_per_second,
            },
        }

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Results saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
