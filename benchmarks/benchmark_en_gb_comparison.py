#!/usr/bin/env python3
"""Comprehensive benchmark comparison for English (GB) G2P configurations.

This script tests all possible configurations of kokorog2p for British English:
- Lexicon-only (gold/silver/both)
- Espeak fallback (with gold/silver/none)
- Goruut fallback (with gold/silver/none)

It measures:
- Accuracy against ground truth
- Processing speed (words/second)
- Phoneme coverage
- OOV handling success rate
- Fallback usage percentage

Usage:
    python benchmark_en_gb_comparison.py
    python benchmark_en_gb_comparison.py --output results.json
    python benchmark_en_gb_comparison.py --verbose
"""

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
    words_per_second: float
    total_time_ms: float
    phoneme_coverage_percent: float
    oov_success_rate: float
    fallback_usage_percent: float
    total_sentences: int
    total_words: int
    successful: int
    failed: int
    errors: list[tuple[int, str, str]] = field(
        default_factory=list
    )  # (id, expected, got)


def load_synthetic_data(language: str = "en-us") -> dict[str, Any]:
    """Load synthetic benchmark data for a language.

    Args:
        language: Language code (e.g., "en-us", "en-gb")

    Returns:
        Parsed JSON data
    """
    # Map language to filename
    lang_file_map = {
        "en-us": "en_us_synthetic.json",
        "en-gb": "en_gb_synthetic.json",
        "de": "de_synthetic.json",
        "fr": "fr_synthetic.json",
        "cs": "cs_synthetic.json",
    }

    filename = lang_file_map.get(language)
    if not filename:
        raise ValueError(f"No synthetic data for language: {language}")

    filepath = Path(__file__).parent / "data" / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Synthetic data file not found: {filepath}")

    with open(filepath) as f:
        return json.load(f)


def create_g2p(language: str, config: dict[str, Any]):
    """Create a G2P instance with the given configuration.

    Args:
        language: Language code
        config: Configuration dictionary

    Returns:
        G2P instance
    """
    if language in ("en-us", "en-gb"):
        from kokorog2p.en import EnglishG2P

        return EnglishG2P(
            language=language,
            use_espeak_fallback=config.get("use_espeak", False),
            use_goruut_fallback=config.get("use_goruut", False),
            load_gold=config.get("load_gold", True),
            load_silver=config.get("load_silver", True),
            use_spacy=False,  # Faster for benchmarking
        )
    elif language == "de":
        from kokorog2p.de import GermanG2P

        return GermanG2P(
            use_espeak_fallback=config.get("use_espeak", False),
            use_goruut_fallback=config.get("use_goruut", False),
            load_gold=config.get("load_gold", True),
        )
    elif language == "fr":
        from kokorog2p.fr import FrenchG2P

        return FrenchG2P(
            use_espeak_fallback=config.get("use_espeak", False),
            use_goruut_fallback=config.get("use_goruut", False),
            load_gold=config.get("load_gold", True),
        )
    elif language == "cs":
        from kokorog2p.cs import CzechG2P

        return CzechG2P(
            use_espeak_fallback=config.get("use_espeak", False),
            use_goruut_fallback=config.get("use_goruut", False),
        )
    else:
        raise ValueError(f"Unsupported language: {language}")


def benchmark_config(
    g2p, data: dict[str, Any], config_name: str, vocab: frozenset[str]
) -> ConfigBenchmark:
    """Benchmark a single G2P configuration.

    Args:
        g2p: G2P instance to test
        data: Synthetic data dictionary
        config_name: Name of this configuration
        vocab: Valid phoneme vocabulary

    Returns:
        ConfigBenchmark results
    """
    sentences = data["sentences"]
    successful = 0
    failed = 0
    total_words = 0
    errors = []
    phonemes_used = set()
    oov_attempted = 0
    oov_successful = 0

    start_time = time.perf_counter()

    for sentence in sentences:
        sentence_id = sentence["id"]
        text = sentence["text"]
        expected_phonemes = sentence["phonemes"]
        is_oov = sentence.get("contains_oov", False)

        # Phonemize
        try:
            tokens = g2p(text)
        except Exception as e:
            failed += 1
            errors.append((sentence_id, expected_phonemes, f"ERROR: {e}"))
            continue

        # Extract ALL phonemes (including punctuation)
        all_phonemes = []
        word_count = 0
        for token in tokens:
            if token.phonemes:
                all_phonemes.append(token.phonemes)
                # Count words (not punctuation)
                if token.is_word and not (
                    len(token.text) == 1 and not token.text.isalnum()
                ):
                    word_count += 1
                # Track phonemes used
                phonemes_used.update(
                    c for c in token.phonemes if c not in (" ", "\t", "\n")
                )

        got_phonemes = " ".join(all_phonemes)
        total_words += word_count

        # Compare (normalize whitespace)
        expected_norm = " ".join(expected_phonemes.split())
        got_norm = " ".join(got_phonemes.split())

        if expected_norm == got_norm:
            successful += 1
            if is_oov:
                oov_successful += 1
        else:
            failed += 1
            if len(errors) < 20:  # Limit error collection
                errors.append((sentence_id, expected_phonemes, got_phonemes))

        if is_oov:
            oov_attempted += 1

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    # Calculate metrics
    total_sentences = len(sentences)
    accuracy = (successful / total_sentences * 100) if total_sentences > 0 else 0
    wps = total_words / (total_time_ms / 1000) if total_time_ms > 0 else 0
    coverage = (len(phonemes_used & vocab) / len(vocab) * 100) if vocab else 0
    oov_rate = (oov_successful / oov_attempted * 100) if oov_attempted > 0 else 0

    # Estimate fallback usage (rough approximation based on OOV sentences)
    # More accurate tracking would require instrumentation of the G2P class
    fallback_usage = oov_attempted / total_sentences * 100 if total_sentences > 0 else 0

    return ConfigBenchmark(
        config_name=config_name,
        accuracy_percent=accuracy,
        words_per_second=wps,
        total_time_ms=total_time_ms,
        phoneme_coverage_percent=coverage,
        oov_success_rate=oov_rate,
        fallback_usage_percent=fallback_usage,
        total_sentences=total_sentences,
        total_words=total_words,
        successful=successful,
        failed=failed,
        errors=errors,
    )


def get_all_configs() -> list[tuple[str, dict[str, Any]]]:
    """Get all configuration combinations to test.

    Returns:
        List of (config_name, config_dict) tuples
    """
    configs = []

    # Lexicon-only configurations
    configs.append(
        (
            "Gold only",
            {
                "load_gold": True,
                "load_silver": False,
                "use_espeak": False,
                "use_goruut": False,
            },
        )
    )
    configs.append(
        (
            "Silver only",
            {
                "load_gold": False,
                "load_silver": True,
                "use_espeak": False,
                "use_goruut": False,
            },
        )
    )
    configs.append(
        (
            "Gold + Silver",
            {
                "load_gold": True,
                "load_silver": True,
                "use_espeak": False,
                "use_goruut": False,
            },
        )
    )

    # Espeak fallback configurations
    configs.append(
        (
            "Gold + Espeak",
            {
                "load_gold": True,
                "load_silver": False,
                "use_espeak": True,
                "use_goruut": False,
            },
        )
    )
    configs.append(
        (
            "Silver + Espeak",
            {
                "load_gold": False,
                "load_silver": True,
                "use_espeak": True,
                "use_goruut": False,
            },
        )
    )
    configs.append(
        (
            "Gold + Silver + Espeak",
            {
                "load_gold": True,
                "load_silver": True,
                "use_espeak": True,
                "use_goruut": False,
            },
        )
    )
    configs.append(
        (
            "Espeak only",
            {
                "load_gold": False,
                "load_silver": False,
                "use_espeak": True,
                "use_goruut": False,
            },
        )
    )

    # Goruut fallback configurations
    configs.append(
        (
            "Gold + Goruut",
            {
                "load_gold": True,
                "load_silver": False,
                "use_espeak": False,
                "use_goruut": True,
            },
        )
    )
    configs.append(
        (
            "Silver + Goruut",
            {
                "load_gold": False,
                "load_silver": True,
                "use_espeak": False,
                "use_goruut": True,
            },
        )
    )
    configs.append(
        (
            "Gold + Silver + Goruut",
            {
                "load_gold": True,
                "load_silver": True,
                "use_espeak": False,
                "use_goruut": True,
            },
        )
    )
    configs.append(
        (
            "Goruut only",
            {
                "load_gold": False,
                "load_silver": False,
                "use_espeak": False,
                "use_goruut": True,
            },
        )
    )

    return configs


def print_results_table(results: list[ConfigBenchmark]) -> None:
    """Print results in a formatted table.

    Args:
        results: List of benchmark results
    """
    print(f"\n{'=' * 120}")
    print("BENCHMARK RESULTS - ALL CONFIGURATIONS")
    print(f"{'=' * 120}")
    print(
        f"{'Configuration':<30} {'Accuracy':>10} {'Speed':>12} {'Coverage':>10} "
        f"{'OOV Rate':>10} {'Sentences':>10}"
    )
    print(f"{'-' * 120}")

    for result in results:
        print(
            f"{result.config_name:<30} "
            f"{result.accuracy_percent:>9.1f}% "
            f"{result.words_per_second:>10.0f} w/s "
            f"{result.phoneme_coverage_percent:>9.1f}% "
            f"{result.oov_success_rate:>9.1f}% "
            f"{result.successful}/{result.total_sentences:>3}"
        )

    print(f"{'=' * 120}")


def print_detailed_results(result: ConfigBenchmark, show_errors: bool = True) -> None:
    """Print detailed results for a single configuration.

    Args:
        result: Benchmark result
        show_errors: Whether to show sample errors
    """
    print(f"\n{'=' * 80}")
    print(f"Configuration: {result.config_name}")
    print(f"{'=' * 80}")
    print(f"Accuracy:         {result.accuracy_percent:.2f}%")
    print(f"Speed:            {result.words_per_second:,.0f} words/second")
    print(f"Total time:       {result.total_time_ms:.2f} ms")
    print(f"Sentences:        {result.successful}/{result.total_sentences}")
    print(f"Words processed:  {result.total_words:,}")
    print(f"Phoneme coverage: {result.phoneme_coverage_percent:.1f}%")
    print(f"OOV success rate: {result.oov_success_rate:.1f}%")

    if show_errors and result.errors:
        print(
            f"\nSample errors (showing {min(5, len(result.errors))}"
            f" of {len(result.errors)}):"
        )
        for sent_id, expected, got in result.errors[:5]:
            print(f"  Sentence {sent_id}:")
            print(f"    Expected: {expected}")
            print(f"    Got:      {got}")


def export_json(results: list[ConfigBenchmark], output_path: Path) -> None:
    """Export results to JSON.

    Args:
        results: List of benchmark results
        output_path: Path to output JSON file
    """
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": [
            {
                "config_name": r.config_name,
                "accuracy_percent": r.accuracy_percent,
                "words_per_second": r.words_per_second,
                "total_time_ms": r.total_time_ms,
                "phoneme_coverage_percent": r.phoneme_coverage_percent,
                "oov_success_rate": r.oov_success_rate,
                "fallback_usage_percent": r.fallback_usage_percent,
                "total_sentences": r.total_sentences,
                "total_words": r.total_words,
                "successful": r.successful,
                "failed": r.failed,
                "error_count": len(r.errors),
            }
            for r in results
        ],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\n✓ Results exported to: {output_path}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark all G2P configurations")
    parser.add_argument(
        "--language",
        "-l",
        default="en-gb",
        help="Language to benchmark (default: en-gb)",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output JSON file path (optional)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed results for each configuration",
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Test only a specific configuration by name",
    )

    args = parser.parse_args()

    # Load synthetic data
    print(f"Loading synthetic data for {args.language}...")
    try:
        data = load_synthetic_data(args.language)
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
        return 1

    print(
        f"Loaded {len(data['sentences'])} sentences "
        f"from {data['metadata']['description']}"
    )

    # Get vocabulary
    from kokorog2p.phonemes import GB_VOCAB, US_VOCAB

    if args.language == "en-gb":
        vocab = GB_VOCAB
    else:
        vocab = US_VOCAB

    # Get configurations to test
    all_configs = get_all_configs()
    if args.config:
        all_configs = [(name, cfg) for name, cfg in all_configs if name == args.config]
        if not all_configs:
            print(f"Error: Configuration '{args.config}' not found")
            print("Available configurations:")
            for name, _ in get_all_configs():
                print(f"  - {name}")
            return 1

    # Check if goruut is available
    goruut_available = False
    try:
        from kokorog2p.backends.goruut import GoruutBackend

        goruut_available = GoruutBackend.is_available()
    except ImportError:
        pass

    if not goruut_available:
        print(
            "\n⚠ Warning: Goruut backend not available, skipping goruut configurations"
        )
        all_configs = [
            (name, cfg) for name, cfg in all_configs if not cfg.get("use_goruut")
        ]

    # Run benchmarks
    print(f"\nRunning {len(all_configs)} configuration(s)...\n")
    results = []

    for config_name, config in all_configs:
        print(f"Testing: {config_name}...", end=" ", flush=True)

        try:
            g2p = create_g2p(args.language, config)
            result = benchmark_config(g2p, data, config_name, vocab)
            results.append(result)
            print(f"✓ {result.accuracy_percent:.1f}% accuracy")

            if args.verbose:
                print_detailed_results(result)
        except Exception as e:
            print(f"✗ ERROR: {e}")
            continue

    # Print summary table
    if results:
        print_results_table(results)

        # Find best configuration
        best_accuracy = max(results, key=lambda r: r.accuracy_percent)
        best_speed = max(results, key=lambda r: r.words_per_second)

        print(
            f"\nBest accuracy:  {best_accuracy.config_name} "
            f"({best_accuracy.accuracy_percent:.1f}%)"
        )
        print(
            f"Fastest:        {best_speed.config_name} "
            f"({best_speed.words_per_second:,.0f} words/sec)"
        )

        # Export to JSON if requested
        if args.output:
            export_json(results, Path(args.output))

    return 0


if __name__ == "__main__":
    sys.exit(main())
