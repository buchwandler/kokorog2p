"""Benchmarks for kokorog2p German G2P conversion.

This module provides benchmarks to measure:
1. G2P conversion accuracy against the gold dictionary
2. G2P conversion throughput
3. End-to-end phonemization throughput for German text

Run with: python -m benchmarks.benchmark_de_g2p
"""

import random
import time
from dataclasses import dataclass, field

from random_sentence_generator import SentenceGenerator


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    name: str
    total_words: int
    successful: int
    failed: int
    total_time_ms: float
    words_per_second: float
    accuracy_percent: float
    errors: list[tuple[str, str, str]] = field(
        default_factory=list
    )  # (word, expected, got)

    def __str__(self) -> str:
        return (
            f"\n{'=' * 60}\n"
            f"Benchmark: {self.name}\n"
            f"{'=' * 60}\n"
            f"Total words:      {self.total_words:,}\n"
            f"Successful:       {self.successful:,}\n"
            f"Failed:           {self.failed:,}\n"
            f"Accuracy:         {self.accuracy_percent:.2f}%\n"
            f"Total time:       {self.total_time_ms:.2f} ms\n"
            f"Words/second:     {self.words_per_second:,.0f}\n"
        )


def load_gold_dictionary() -> dict[str, str]:
    """Load the German gold dictionary.

    Returns:
        Dictionary mapping words to expected phonemes.
    """
    import importlib.resources
    import json

    from kokorog2p.de import data

    with importlib.resources.open_text(data, "de_gold.json") as f:
        return json.load(f)


def benchmark_accuracy(
    g2p,
    gold: dict[str, str],
    sample_size: int | None = None,
    name: str = "Accuracy vs Gold Dictionary",
) -> BenchmarkResult:
    """Benchmark G2P accuracy against gold dictionary.

    Args:
        g2p: The G2P instance to test.
        gold: Gold dictionary mapping words to expected phonemes.
        sample_size: If set, only test this many random samples.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with accuracy data.
    """
    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    # Optionally sample
    items = list(gold.items())
    if sample_size and sample_size < len(items):
        items = random.sample(items, sample_size)

    start_time = time.perf_counter()

    for word, expected in items:
        try:
            tokens = g2p(word)
            if tokens and tokens[0].phonemes:
                got = tokens[0].phonemes
                # Normalize for comparison (strip stress markers for fair comparison)
                expected_norm = expected.replace("ˈ", "").replace("ˌ", "").strip()
                got_norm = got.replace("ˈ", "").replace("ˌ", "").strip()

                if expected_norm == got_norm:
                    successful += 1
                else:
                    failed += 1
                    if len(errors) < 100:
                        errors.append((word, expected_norm, got_norm))
            else:
                failed += 1
                if len(errors) < 100:
                    errors.append((word, expected, "None"))
        except Exception as e:
            failed += 1
            if len(errors) < 100:
                errors.append((word, expected, f"Error: {e}"))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    total_words = len(items)

    return BenchmarkResult(
        name=name,
        total_words=total_words,
        successful=successful,
        failed=failed,
        total_time_ms=total_time_ms,
        words_per_second=total_words / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=(successful / total_words * 100) if total_words else 0,
        errors=errors,
    )


def benchmark_throughput(
    g2p,
    words: list[str],
    name: str = "G2P Throughput",
) -> BenchmarkResult:
    """Benchmark G2P conversion throughput.

    Args:
        g2p: The G2P instance to test.
        words: List of words to convert.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with timing data.
    """
    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words:
        try:
            tokens = g2p(word)
            if tokens and tokens[0].phonemes:
                successful += 1
            else:
                failed += 1
                if len(errors) < 100:
                    errors.append((word, "expected phonemes", "None"))
        except Exception as e:
            failed += 1
            if len(errors) < 100:
                errors.append((word, "no error", str(e)))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=len(words),
        successful=successful,
        failed=failed,
        total_time_ms=total_time_ms,
        words_per_second=len(words) / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=(successful / len(words) * 100) if words else 0,
        errors=errors,
    )


def benchmark_sentence_throughput(
    g2p,
    sentences: list[str],
    name: str = "Sentence Throughput",
) -> BenchmarkResult:
    """Benchmark sentence phonemization throughput.

    Args:
        g2p: The G2P instance to test.
        sentences: List of sentences to convert.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with timing data.
    """
    total_chars = 0
    successful = 0

    start_time = time.perf_counter()

    for sentence in sentences:
        tokens = g2p(sentence)
        total_chars += len(sentence)
        if tokens:
            successful += 1

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=len(sentences),
        successful=successful,
        failed=len(sentences) - successful,
        total_time_ms=total_time_ms,
        words_per_second=total_chars / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=(successful / len(sentences) * 100) if sentences else 0,
    )


def benchmark_lexicon_coverage(
    g2p,
    words: list[str],
    name: str = "Lexicon Coverage",
) -> BenchmarkResult:
    """Benchmark how many words are found in the lexicon.

    Args:
        g2p: The G2P instance to test.
        words: List of words to check.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with coverage data.
    """
    in_lexicon = 0
    not_in_lexicon: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words:
        if g2p._lexicon and g2p._lexicon.is_known(word):
            in_lexicon += 1
        else:
            if len(not_in_lexicon) < 100:
                not_in_lexicon.append((word, "in lexicon", "not found"))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=len(words),
        successful=in_lexicon,
        failed=len(words) - in_lexicon,
        total_time_ms=total_time_ms,
        words_per_second=len(words) / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=(in_lexicon / len(words) * 100) if words else 0,
        errors=not_in_lexicon,
    )


def benchmark_phoneme_output(
    g2p,
    words: list[str],
    name: str = "Phoneme Output Sample",
) -> BenchmarkResult:
    """Sample phoneme outputs for inspection.

    Args:
        g2p: The G2P instance to test.
        words: List of words to convert.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with sample outputs in errors field.
    """
    samples: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words[:100]:  # Only sample first 100
        tokens = g2p(word)
        phonemes = tokens[0].phonemes if tokens else "None"
        samples.append((word, "", phonemes or "None"))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=len(words),
        successful=len(words),
        failed=0,
        total_time_ms=total_time_ms,
        words_per_second=len(words) / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=100.0,
        errors=samples,
    )


def run_all_benchmarks(
    sample_size: int = 10000,
    seed: int = 42,
    verbose: bool = True,
) -> list[BenchmarkResult]:
    """Run all German G2P benchmarks.

    Args:
        sample_size: Number of words to sample for throughput benchmarks.
        seed: Random seed for reproducibility.
        verbose: Whether to print results.

    Returns:
        List of BenchmarkResult objects.
    """
    random.seed(seed)
    results: list[BenchmarkResult] = []

    print("Loading German gold dictionary...")
    gold = load_gold_dictionary()
    print(f"Total entries in gold dictionary: {len(gold):,}")

    # Import German G2P
    print("\nInitializing German G2P...")
    from kokorog2p.de import GermanG2P

    g2p = GermanG2P()
    print(f"Lexicon entries: {len(g2p._lexicon):,}" if g2p._lexicon else "No lexicon")

    generator = SentenceGenerator(seed=seed, language="de")

    print("\nRunning benchmarks...\n")

    # Benchmark 1: Accuracy vs Gold Dictionary (sampled)
    result = benchmark_accuracy(
        g2p,
        gold,
        sample_size=sample_size,
        name="German - Accuracy vs Gold (sampled)",
    )
    results.append(result)
    if verbose:
        print(result)
        if result.errors:
            print("Sample errors (word, expected, got):")
            for word, expected, got in result.errors[:10]:
                print(f"  {word}: {expected} -> {got}")

    # Benchmark 2: G2P Throughput with common words
    word_pool = generator.words_data["base_words"]
    sample_words = (word_pool * (sample_size // len(word_pool) + 1))[:sample_size]
    random.shuffle(sample_words)
    result = benchmark_throughput(
        g2p,
        sample_words,
        name="German - G2P Throughput",
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 3: Lexicon coverage
    all_words = list(gold.keys())[:sample_size]
    result = benchmark_lexicon_coverage(
        g2p,
        all_words,
        name="German - Lexicon Coverage",
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 4: Sample phoneme outputs
    sample_words_for_output = random.sample(list(gold.keys()), min(100, len(gold)))
    result = benchmark_phoneme_output(
        g2p,
        sample_words_for_output,
        name="German - Phoneme Output Sample",
    )
    results.append(result)
    if verbose:
        print(result)
        print("Sample outputs (word -> phonemes):")
        for word, _, phonemes in result.errors[:20]:
            print(f"  {word} -> {phonemes}")

    # Benchmark 5: Sentence throughput
    sentence_cases = generator.generate_batch(total=1000, simple=True)
    sample_sentences = [tc.text for tc in sentence_cases]

    result = benchmark_sentence_throughput(
        g2p,
        sample_sentences,
        name="German - Sentence Throughput",
    )
    results.append(result)
    if verbose:
        print(result)

    # Summary
    if verbose:
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        for r in results:
            print(
                f"{r.name:45} | {r.accuracy_percent:6.2f}% "
                f"| {r.words_per_second:10,.0f} words/sec"
            )

    return results


def main():
    """Run benchmarks from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run kokorog2p German benchmarks")
    parser.add_argument(
        "--sample-size",
        "-n",
        type=int,
        default=10000,
        help="Number of words to sample (default: 10000)",
    )
    parser.add_argument(
        "--seed", "-s", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress verbose output"
    )

    args = parser.parse_args()

    results = run_all_benchmarks(
        sample_size=args.sample_size,
        seed=args.seed,
        verbose=not args.quiet,
    )

    # Return non-zero if accuracy benchmark has <80% accuracy
    accuracy_results = [r for r in results if "Accuracy" in r.name]
    if any(r.accuracy_percent < 80 for r in accuracy_results):
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
