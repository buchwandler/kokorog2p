"""Benchmarks for kokorog2p French G2P conversion.

This module provides benchmarks to measure:
1. G2P conversion accuracy against gold dictionary
2. G2P conversion throughput
3. End-to-end phonemization throughput for French text

Run with: python -m benchmarks.benchmark_fr_g2p
"""

import importlib.resources
import json
import random
import time
from dataclasses import dataclass, field

from benchmarks.random_sentence_generator import SentenceGenerator


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
    """Load the French gold dictionary.

    Returns:
        Dictionary mapping words to phonemes.
    """
    from kokorog2p.fr import data

    with importlib.resources.open_text(data, "fr_gold.json") as f:
        gold = json.load(f)

    # Flatten heteronyms to just use DEFAULT or first value
    result: dict[str, str] = {}
    for word, phonemes in gold.items():
        if isinstance(phonemes, dict):
            result[word] = phonemes.get("DEFAULT", list(phonemes.values())[0])
        else:
            result[word] = phonemes

    return result


def benchmark_accuracy(
    g2p,
    gold: dict[str, str],
    name: str = "Accuracy vs Gold Dictionary",
) -> BenchmarkResult:
    """Benchmark G2P accuracy against gold dictionary.

    Args:
        g2p: The G2P instance to test.
        gold: Gold dictionary mapping words to expected phonemes.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with accuracy data.
    """
    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word, expected in gold.items():
        try:
            tokens = g2p(word)
            if tokens and tokens[0].phonemes:
                got = tokens[0].phonemes
                # Normalize for comparison
                expected_norm = expected.strip()
                got_norm = got.strip()

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
    total_words = len(gold)

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


def benchmark_number_expansion(
    name: str = "Number Expansion",
) -> BenchmarkResult:
    """Benchmark number-to-French conversion.

    Args:
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with accuracy data.
    """
    from kokorog2p.fr.numbers import number_to_french

    # Test cases: (number, expected French)
    test_cases = [
        (0, "zéro"),
        (1, "un"),
        (10, "dix"),
        (15, "quinze"),
        (21, "vingt-et-un"),
        (42, "quarante-deux"),
        (70, "soixante-dix"),
        (71, "soixante-et-onze"),
        (80, "quatre-vingts"),
        (81, "quatre-vingt-un"),
        (90, "quatre-vingt-dix"),
        (91, "quatre-vingt-onze"),
        (100, "cent"),
        (200, "deux-cents"),
        (201, "deux-cent-un"),
        (1000, "mille"),
        (2000, "deux-mille"),
        (2021, "deux-mille-vingt-et-un"),
        (1000000, "un-million"),
        (2000000, "deux-millions"),
    ]

    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for number, expected in test_cases:
        got = number_to_french(number)
        if got == expected:
            successful += 1
        else:
            failed += 1
            errors.append((str(number), expected, got))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    total = len(test_cases)

    return BenchmarkResult(
        name=name,
        total_words=total,
        successful=successful,
        failed=failed,
        total_time_ms=total_time_ms,
        words_per_second=total / (total_time_ms / 1000) if total_time_ms > 0 else 0,
        accuracy_percent=(successful / total * 100) if total else 0,
        errors=errors,
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
    sample_size: int = 1000,
    seed: int = 42,
    verbose: bool = True,
    use_spacy: bool = True,
) -> list[BenchmarkResult]:
    """Run all French G2P benchmarks.

    Args:
        sample_size: Number of words to sample for throughput benchmarks.
        seed: Random seed for reproducibility.
        verbose: Whether to print results.
        use_spacy: Whether to use spaCy for tokenization.

    Returns:
        List of BenchmarkResult objects.
    """
    random.seed(seed)
    results: list[BenchmarkResult] = []

    print("Loading French gold dictionary...")
    gold = load_gold_dictionary()
    print(f"Total gold entries: {len(gold):,}")

    # Import French G2P
    print("\nInitializing French G2P...")
    from kokorog2p.fr import FrenchG2P

    g2p = FrenchG2P(use_spacy=use_spacy, use_espeak_fallback=True)

    generator = SentenceGenerator(seed=seed, language="fr")

    print("\nRunning benchmarks...\n")

    # Benchmark 1: Accuracy vs Gold Dictionary
    result = benchmark_accuracy(
        g2p,
        gold,
        name="French - Accuracy vs Gold Dictionary",
    )
    results.append(result)
    if verbose:
        print(result)
        if result.errors:
            print("Sample errors (word, expected, got):")
            for word, expected, got in result.errors[:10]:
                print(f"  {word}: {expected} -> {got}")

    # Benchmark 2: G2P Throughput
    word_pool = generator.words_data["base_words"]
    sample_words = (word_pool * (sample_size // len(word_pool) + 1))[:sample_size]
    random.shuffle(sample_words)
    result = benchmark_throughput(
        g2p,
        sample_words,
        name="French - G2P Throughput",
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 3: Number expansion
    result = benchmark_number_expansion(
        name="French - Number Expansion",
    )
    results.append(result)
    if verbose:
        print(result)
        if result.errors:
            print("Number errors (number, expected, got):")
            for num, expected, got in result.errors:
                print(f"  {num}: {expected} -> {got}")

    # Benchmark 4: Sample phoneme outputs
    result = benchmark_phoneme_output(
        g2p,
        sample_words,
        name="French - Phoneme Output Sample",
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
        name="French - Sentence Throughput",
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

    parser = argparse.ArgumentParser(description="Run kokorog2p French benchmarks")
    parser.add_argument(
        "--sample-size",
        "-n",
        type=int,
        default=1000,
        help="Number of words to sample for throughput (default: 1000)",
    )
    parser.add_argument(
        "--seed", "-s", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress verbose output"
    )
    parser.add_argument(
        "--no-spacy", action="store_true", help="Disable spaCy tokenization"
    )

    args = parser.parse_args()

    results = run_all_benchmarks(
        sample_size=args.sample_size,
        seed=args.seed,
        verbose=not args.quiet,
        use_spacy=not args.no_spacy,
    )

    # Return non-zero if accuracy benchmark has <80% accuracy
    accuracy_results = [r for r in results if "Accuracy" in r.name]
    if any(r.accuracy_percent < 80 for r in accuracy_results):
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
