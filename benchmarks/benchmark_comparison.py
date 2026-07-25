#!/usr/bin/env python3
"""Master benchmark runner for all languages.

This script runs all language-specific benchmark comparison scripts and
generates a comprehensive summary table comparing accuracy and performance
across all languages and configurations.

Usage:
    python benchmark_comparison.py
    python benchmark_comparison.py --languages en-us en-gb de
    python benchmark_comparison.py --output results.json
    python benchmark_comparison.py --verbose
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LanguageBenchmark:
    """Results from benchmarking a single language."""

    language: str
    language_name: str
    total_sentences: int
    best_accuracy: float
    best_config: str
    fastest_speed: float
    fastest_config: str
    gold_only_accuracy: float
    gold_silver_accuracy: float
    gold_espeak_accuracy: float
    gold_silver_espeak_accuracy: float
    espeak_only_accuracy: float
    all_configs: dict[str, dict[str, Any]]
    success: bool = True
    error_message: str = ""


# Language metadata
LANGUAGES = {
    "en-us": {
        "name": "English (US)",
        "script": "benchmark_en_us_comparison.py",
        "enabled": True,
    },
    "en-gb": {
        "name": "English (GB)",
        "script": "benchmark_en_gb_comparison.py",
        "enabled": True,
    },
    "de": {
        "name": "German",
        "script": "benchmark_de_comparison.py",
        "enabled": True,
    },
    "fr": {
        "name": "French",
        "script": "benchmark_fr_comparison.py",
        "enabled": True,
    },
    "es": {
        "name": "Spanish",
        "script": "benchmark_es_comparison.py",
        "enabled": True,
    },
    "it": {
        "name": "Italian",
        "script": "benchmark_it_comparison.py",
        "enabled": True,
    },
    "pt-br": {
        "name": "Portuguese (BR)",
        "script": "benchmark_pt_br_comparison.py",
        "enabled": True,
    },
    "ja": {
        "name": "Japanese",
        "script": "benchmark_ja_comparison.py",
        "enabled": True,
    },
    "ko": {
        "name": "Korean",
        "script": "benchmark_ko_comparison.py",
        "enabled": True,
    },
    "zh": {
        "name": "Chinese",
        "script": "benchmark_zh_comparison.py",
        "enabled": True,
    },
}


def run_language_benchmark(
    language: str, script_path: Path, verbose: bool = False
) -> dict[str, Any] | None:
    """Run a single language benchmark script.

    Args:
        language: Language code (e.g., "en-us")
        script_path: Path to the benchmark script
        verbose: Whether to show verbose output

    Returns:
        Parsed JSON results or None if failed
    """
    # Create temp output file
    output_file = Path(f"/tmp/benchmark_{language}_{int(time.time())}.json")

    try:
        # Run the benchmark script with JSON output
        cmd = [sys.executable, str(script_path), "--output", str(output_file)]

        if verbose:
            print(f"\n{'=' * 80}")
            print(f"Running: {' '.join(cmd)}")
            print(f"{'=' * 80}\n")

        result = subprocess.run(
            cmd,
            capture_output=not verbose,
            text=True,
            timeout=300,  # 5 minute timeout
            check=False,
        )

        if result.returncode != 0:
            print(f"  ✗ Failed with return code {result.returncode}")
            if not verbose and result.stderr:
                print(f"    Error: {result.stderr[:200]}")
            return None

        # Read the JSON output
        if output_file.exists():
            with open(output_file) as f:
                return json.load(f)
        else:
            print(f"  ✗ Output file not created: {output_file}")
            return None

    except subprocess.TimeoutExpired:
        print("  ✗ Timeout after 5 minutes")
        return None
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None
    finally:
        # Clean up temp file
        if output_file.exists():
            output_file.unlink()


def parse_benchmark_results(
    language: str, language_name: str, results: dict[str, Any]
) -> LanguageBenchmark:
    """Parse benchmark results into LanguageBenchmark dataclass.

    Args:
        language: Language code
        language_name: Human-readable language name
        results: Raw benchmark results

    Returns:
        LanguageBenchmark instance
    """
    # Handle different JSON formats (results vs configurations)
    all_results = results.get("results", results.get("configurations", []))

    configs = {}
    for result in all_results:
        # Handle different field names (config_name vs name)
        config_name = result.get("config_name", result.get("name", "Unknown"))

        # Handle different speed metrics (words_per_second or sentences_per_second)
        speed = result.get("words_per_second", result.get("sentences_per_second", 0))

        # Get total sentences from result or dataset metadata
        total_sentences = result.get(
            "total_sentences", results.get("total_sentences", 0)
        )

        # Get coverage (may not exist in all formats)
        coverage = result.get(
            "phoneme_coverage_percent", result.get("unique_phonemes", 0)
        )

        configs[config_name] = {
            "accuracy": result["accuracy_percent"],
            "speed": speed,
            "sentences": f"{result['successful']}/{total_sentences}",
            "total_sentences": total_sentences,
            "coverage": coverage,
        }

    # Find best configurations
    if not all_results:
        return LanguageBenchmark(
            language=language,
            language_name=language_name,
            total_sentences=0,
            best_accuracy=0,
            best_config="N/A",
            fastest_speed=0,
            fastest_config="N/A",
            gold_only_accuracy=0,
            gold_silver_accuracy=0,
            gold_espeak_accuracy=0,
            gold_silver_espeak_accuracy=0,
            espeak_only_accuracy=0,
            all_configs=configs,
            success=False,
            error_message="No results",
        )

    best_accuracy_result = max(all_results, key=lambda r: r["accuracy_percent"])

    # Handle different speed metrics
    def get_speed(r):
        return r.get("words_per_second", r.get("sentences_per_second", 0))

    fastest_result = max(all_results, key=get_speed)

    # Get specific configuration accuracies
    def get_accuracy(config_name: str) -> float:
        for r in all_results:
            # Handle different field names
            r_name = r.get("config_name", r.get("name", ""))
            if r_name == config_name:
                return r["accuracy_percent"]
        return 0.0

    # Get total sentences from result or dataset metadata
    total_sentences = best_accuracy_result.get(
        "total_sentences", results.get("total_sentences", 0)
    )

    # Get config name from result
    best_config = best_accuracy_result.get(
        "config_name", best_accuracy_result.get("name", "Unknown")
    )
    fastest_config = fastest_result.get(
        "config_name", fastest_result.get("name", "Unknown")
    )

    return LanguageBenchmark(
        language=language,
        language_name=language_name,
        total_sentences=total_sentences,
        best_accuracy=best_accuracy_result["accuracy_percent"],
        best_config=best_config,
        fastest_speed=get_speed(fastest_result),
        fastest_config=fastest_config,
        gold_only_accuracy=get_accuracy("Gold only"),
        gold_silver_accuracy=get_accuracy("Gold + Silver"),
        gold_espeak_accuracy=get_accuracy("Gold + Espeak"),
        gold_silver_espeak_accuracy=get_accuracy("Gold + Silver + Espeak"),
        espeak_only_accuracy=get_accuracy("Espeak only"),
        all_configs=configs,
        success=True,
    )


def print_summary_table(benchmarks: list[LanguageBenchmark]) -> None:
    """Print a comprehensive summary table.

    Args:
        benchmarks: List of benchmark results
    """
    print(f"\n{'=' * 140}")
    print("COMPREHENSIVE BENCHMARK SUMMARY - ALL LANGUAGES")
    print(f"{'=' * 140}")
    print(
        f"{'Language':<18} {'Sentences':>10} {'Best Acc':>10} {'Best Config':<25} "
        f"{'Fastest':>12} {'Gold+Ag+Esp':>12}"
    )
    print(f"{'-' * 140}")

    for bench in benchmarks:
        if not bench.success:
            print(
                f"{bench.language_name:<18} {'N/A':>10} {'N/A':>10} "
                f"{'ERROR: ' + bench.error_message:<25} {'N/A':>12} {'N/A':>12}"
            )
            continue

        print(
            f"{bench.language_name:<18} "
            f"{bench.total_sentences:>10} "
            f"{bench.best_accuracy:>9.1f}% "
            f"{bench.best_config:<25} "
            f"{bench.fastest_speed:>10.0f} w/s "
            f"{bench.gold_silver_espeak_accuracy:>10.1f}%"
        )

    print(f"{'=' * 140}\n")


def print_detailed_table(benchmarks: list[LanguageBenchmark]) -> None:
    """Print detailed configuration comparison table.

    Args:
        benchmarks: List of benchmark results
    """
    print(f"\n{'=' * 120}")
    print("DETAILED CONFIGURATION COMPARISON")
    print(f"{'=' * 120}")
    print(
        f"{'Language':<18} {'Gold Only':>11} {'Gold+Silver':>13} {'Gold+Espeak':>13} "
        f"{'Gold+Ag+Esp':>13} {'Espeak Only':>13}"
    )
    print(f"{'-' * 120}")

    for bench in benchmarks:
        if not bench.success:
            continue

        print(
            f"{bench.language_name:<18} "
            f"{bench.gold_only_accuracy:>10.1f}% "
            f"{bench.gold_silver_accuracy:>12.1f}% "
            f"{bench.gold_espeak_accuracy:>12.1f}% "
            f"{bench.gold_silver_espeak_accuracy:>12.1f}% "
            f"{bench.espeak_only_accuracy:>12.1f}%"
        )

    print(f"{'=' * 120}\n")


def print_performance_table(benchmarks: list[LanguageBenchmark]) -> None:
    """Print performance comparison table.

    Args:
        benchmarks: List of benchmark results
    """
    print(f"\n{'=' * 100}")
    print("PERFORMANCE COMPARISON (words/second)")
    print(f"{'=' * 100}")
    print(
        f"{'Language':<18} {'Fastest Config':<30} {'Speed':>15} {'Best Accuracy':>12}"
    )
    print(f"{'-' * 100}")

    # Sort by fastest speed
    sorted_benchmarks = sorted(
        [b for b in benchmarks if b.success],
        key=lambda b: b.fastest_speed,
        reverse=True,
    )

    for bench in sorted_benchmarks:
        print(
            f"{bench.language_name:<18} "
            f"{bench.fastest_config:<30} "
            f"{bench.fastest_speed:>13,.0f} w/s "
            f"{bench.best_accuracy:>10.1f}%"
        )

    print(f"{'=' * 100}\n")


def export_results(benchmarks: list[LanguageBenchmark], output_path: Path) -> None:
    """Export all results to JSON.

    Args:
        benchmarks: List of benchmark results
        output_path: Path to output JSON file
    """
    data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "languages": [
            {
                "language": b.language,
                "language_name": b.language_name,
                "total_sentences": b.total_sentences,
                "best_accuracy": b.best_accuracy,
                "best_config": b.best_config,
                "fastest_speed": b.fastest_speed,
                "fastest_config": b.fastest_config,
                "gold_only_accuracy": b.gold_only_accuracy,
                "gold_silver_accuracy": b.gold_silver_accuracy,
                "gold_espeak_accuracy": b.gold_espeak_accuracy,
                "gold_silver_espeak_accuracy": b.gold_silver_espeak_accuracy,
                "espeak_only_accuracy": b.espeak_only_accuracy,
                "all_configs": b.all_configs,
                "success": b.success,
                "error_message": b.error_message,
            }
            for b in benchmarks
        ],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✓ Results exported to: {output_path}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run benchmarks for all languages and generate summary"
    )
    parser.add_argument(
        "--languages",
        "-l",
        nargs="+",
        help="Specific languages to benchmark (default: all)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file path (optional)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output from benchmark scripts",
    )
    parser.add_argument(
        "--skip-errors",
        action="store_true",
        help="Continue even if some benchmarks fail",
    )

    args = parser.parse_args()

    # Determine which languages to benchmark
    if args.languages:
        languages_to_run = {
            lang: LANGUAGES[lang]
            for lang in args.languages
            if lang in LANGUAGES and LANGUAGES[lang]["enabled"]
        }
        if not languages_to_run:
            print("Error: No valid languages specified")
            print(f"Available: {', '.join(LANGUAGES.keys())}")
            return 1
    else:
        languages_to_run = {
            lang: meta for lang, meta in LANGUAGES.items() if meta["enabled"]
        }

    print(f"\n{'=' * 80}")
    print(f"RUNNING BENCHMARKS FOR {len(languages_to_run)} LANGUAGES")
    print(f"{'=' * 80}\n")

    benchmarks_dir = Path(__file__).parent
    benchmarks = []

    for language, meta in languages_to_run.items():
        script_path = benchmarks_dir / meta["script"]

        if not script_path.exists():
            print(f"✗ {meta['name']:<20} - Script not found: {meta['script']}")
            benchmarks.append(
                LanguageBenchmark(
                    language=language,
                    language_name=meta["name"],
                    total_sentences=0,
                    best_accuracy=0,
                    best_config="N/A",
                    fastest_speed=0,
                    fastest_config="N/A",
                    gold_only_accuracy=0,
                    gold_silver_accuracy=0,
                    gold_espeak_accuracy=0,
                    gold_silver_espeak_accuracy=0,
                    espeak_only_accuracy=0,
                    all_configs={},
                    success=False,
                    error_message="Script not found",
                )
            )
            continue

        print(f"Running {meta['name']:<20}...", end=" ", flush=True)
        start_time = time.perf_counter()

        results = run_language_benchmark(language, script_path, args.verbose)

        elapsed = time.perf_counter() - start_time

        if results:
            benchmark = parse_benchmark_results(language, meta["name"], results)
            benchmarks.append(benchmark)
            print(f"✓ {benchmark.best_accuracy:.1f}% accuracy ({elapsed:.1f}s)")
        else:
            benchmarks.append(
                LanguageBenchmark(
                    language=language,
                    language_name=meta["name"],
                    total_sentences=0,
                    best_accuracy=0,
                    best_config="N/A",
                    fastest_speed=0,
                    fastest_config="N/A",
                    gold_only_accuracy=0,
                    gold_silver_accuracy=0,
                    gold_espeak_accuracy=0,
                    gold_silver_espeak_accuracy=0,
                    espeak_only_accuracy=0,
                    all_configs={},
                    success=False,
                    error_message="Benchmark failed",
                )
            )
            if not args.skip_errors:
                print("\nStopping due to error. Use --skip-errors to continue.")
                return 1

    # Print summary tables
    print_summary_table(benchmarks)
    print_detailed_table(benchmarks)
    print_performance_table(benchmarks)

    # Calculate overall statistics
    successful = [b for b in benchmarks if b.success]
    if successful:
        avg_accuracy = sum(b.best_accuracy for b in successful) / len(successful)
        avg_gold_silver_espeak = sum(
            b.gold_silver_espeak_accuracy for b in successful
        ) / len(successful)
        total_sentences = sum(b.total_sentences for b in successful)

        print(f"\n{'=' * 80}")
        print("OVERALL STATISTICS")
        print(f"{'=' * 80}")
        print(f"Languages tested:              {len(successful)}/{len(benchmarks)}")
        print(f"Total sentences:               {total_sentences:,}")
        print(f"Average best accuracy:         {avg_accuracy:.1f}%")
        print(f"Average Gold+Silver+Espeak:    {avg_gold_silver_espeak:.1f}%")
        print(
            f"Perfect accuracy (100%):       "
            f"{sum(1 for b in successful if b.best_accuracy >= 99.9)}/{len(successful)}"
        )
        print(f"{'=' * 80}\n")

    # Export to JSON if requested
    if args.output:
        export_results(benchmarks, args.output)

    # Return error code if any benchmarks failed
    if any(not b.success for b in benchmarks):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
