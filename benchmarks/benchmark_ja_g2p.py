"""Benchmarks for kokorog2p Japanese G2P conversion.

This module provides benchmarks to measure:
1. G2P conversion throughput
2. Vocabulary coverage validation
3. End-to-end phonemization throughput for Japanese text
4. Comparison between pyopenjtalk and cutlet backends

Run with: python -m benchmarks.benchmark_ja_g2p
"""

import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path


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


def load_word_list(path: Path) -> list[str]:
    """Load a word list from a text file.

    Args:
        path: Path to the word list file (one word per line).

    Returns:
        List of words.
    """
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def benchmark_g2p_throughput(
    g2p,
    words: list[str],
    name: str = "G2P Throughput",
) -> BenchmarkResult:
    """Benchmark G2P conversion throughput for Japanese words.

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
    """Benchmark sentence phonemization throughput for Japanese.

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


def benchmark_vocab_validation(
    g2p,
    words: list[str],
    name: str = "Vocab Validation",
) -> BenchmarkResult:
    """Validate that all generated phonemes are in Kokoro vocabulary.

    Args:
        g2p: The G2P instance to test.
        words: List of words to convert and validate.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with validation data.
    """
    from kokorog2p.vocab import validate_for_kokoro

    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words:
        tokens = g2p(word)
        if not tokens or not tokens[0].phonemes:
            failed += 1
            if len(errors) < 100:
                errors.append((word, "expected phonemes", "None"))
            continue

        # Get the phoneme string (without pitch markers)
        phonemes = tokens[0].phonemes
        # Japanese phonemes include pitch markers like _^- at the end
        # We need to extract just the phoneme part
        if phonemes:
            # Split phonemes from pitch markers (pitch markers are _^-j)
            phoneme_part = ""
            for char in phonemes:
                if char not in "_^-j":
                    phoneme_part += char

            is_valid, invalid = validate_for_kokoro(phoneme_part)
            if is_valid:
                successful += 1
            else:
                failed += 1
                if len(errors) < 100:
                    errors.append((word, phoneme_part, f"Invalid: {invalid}"))
        else:
            failed += 1

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


def benchmark_encoding(
    g2p,
    words: list[str],
    name: str = "Kokoro Encoding",
) -> BenchmarkResult:
    """Benchmark phoneme-to-token encoding speed for Japanese.

    Args:
        g2p: The G2P instance to test.
        words: List of words to convert and encode.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with timing and validation data.
    """
    from kokorog2p.vocab import encode, validate_for_kokoro

    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words:
        tokens = g2p(word)
        if not tokens or not tokens[0].phonemes:
            failed += 1
            continue

        phonemes = tokens[0].phonemes
        # Extract phoneme part without pitch markers
        phoneme_part = ""
        for char in phonemes:
            if char not in "_^-j":
                phoneme_part += char

        is_valid, invalid = validate_for_kokoro(phoneme_part)
        if is_valid:
            ids = encode(phoneme_part)
            if ids:
                successful += 1
            else:
                failed += 1
                if len(errors) < 100:
                    errors.append((word, phoneme_part, "Empty encoding"))
        else:
            failed += 1
            if len(errors) < 100:
                errors.append((word, phoneme_part, f"Invalid chars: {invalid}"))

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


def benchmark_phoneme_output(
    g2p,
    words: list[str],
    name: str = "Phoneme Output Sample",
) -> BenchmarkResult:
    """Sample phoneme outputs for inspection.

    This benchmark doesn't measure accuracy but collects sample outputs
    for manual inspection of the G2P quality.

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
    sample_size: int = 5000,
    seed: int = 42,
    verbose: bool = True,
) -> list[BenchmarkResult]:
    """Run all Japanese G2P benchmarks.

    Args:
        sample_size: Number of words to sample for each benchmark.
        seed: Random seed for reproducibility.
        verbose: Whether to print results.

    Returns:
        List of BenchmarkResult objects.
    """
    random.seed(seed)
    results: list[BenchmarkResult] = []

    # Get data directory
    data_dir = Path(__file__).parent.parent / "kokorog2p" / "ja" / "data"
    if not data_dir.exists():
        data_dir = Path(__file__).parent.parent / "ja" / "data"

    word_list_path = data_dir / "ja_words.txt"

    print(f"Loading word list from {word_list_path}...")

    # Load Japanese word list
    all_words = load_word_list(word_list_path)
    print(f"Total words available: {len(all_words):,}")

    # Sample words
    sample_words = random.sample(all_words, min(sample_size, len(all_words)))

    # Import Japanese G2P
    print("\nInitializing Japanese G2P components...")
    from kokorog2p.ja import JapaneseG2P

    # Initialize with pyopenjtalk backend (default)
    g2p_pyopenjtalk = JapaneseG2P(version="pyopenjtalk")

    print("\nRunning benchmarks...\n")

    # Benchmark 1: G2P Throughput (pyopenjtalk)
    result = benchmark_g2p_throughput(
        g2p_pyopenjtalk,
        sample_words,
        name="Japanese - G2P Throughput (pyopenjtalk)",
    )
    results.append(result)
    if verbose:
        print(result)
        if result.errors:
            print("Sample errors (word, expected, got):")
            for word, expected_val, got in result.errors[:10]:
                print(f"  {word}: {expected_val} -> {got}")

    # Benchmark 2: Vocabulary validation
    result = benchmark_vocab_validation(
        g2p_pyopenjtalk,
        sample_words[: min(1000, len(sample_words))],
        name="Japanese - Vocab Validation",
    )
    results.append(result)
    if verbose:
        print(result)
        if result.errors:
            print("Sample errors (word, phonemes, issue):")
            for word, phonemes, issue in result.errors[:10]:
                print(f"  {word}: {phonemes} -> {issue}")

    # Benchmark 3: Kokoro encoding
    result = benchmark_encoding(
        g2p_pyopenjtalk,
        sample_words[: min(1000, len(sample_words))],
        name="Japanese - Kokoro Encoding",
    )
    results.append(result)
    if verbose:
        print(result)
        if result.errors:
            print("Sample errors (word, phonemes, issue):")
            for word, phonemes, issue in result.errors[:10]:
                print(f"  {word}: {phonemes} -> {issue}")

    # Benchmark 4: Sample phoneme outputs
    result = benchmark_phoneme_output(
        g2p_pyopenjtalk,
        sample_words,
        name="Japanese - Phoneme Output Sample",
    )
    results.append(result)
    if verbose:
        print(result)
        print("Sample outputs (word -> phonemes):")
        for word, _, phonemes in result.errors[:20]:
            print(f"  {word} -> {phonemes}")

    # Benchmark 5: Sentence throughput
    sample_sentences = [
        "こんにちは、世界。",
        "今日はいい天気ですね。",
        "東京は日本の首都です。",
        "私は日本語を勉強しています。",
        "美味しいラーメンを食べました。",
        "電車で会社に行きます。",
        "週末は映画を見に行きたいです。",
        "この本はとても面白いです。",
        "明日の朝、早く起きなければなりません。",
        "彼女は歌がとても上手です。",
    ] * 100  # 1000 sentences

    result = benchmark_sentence_throughput(
        g2p_pyopenjtalk,
        sample_sentences,
        name="Japanese - Sentence Throughput",
    )
    results.append(result)
    if verbose:
        print(result)

    # Try cutlet backend if available
    try:
        print("\nTrying cutlet backend...")
        g2p_cutlet = JapaneseG2P(version="cutlet")

        # Benchmark 6: G2P Throughput (cutlet)
        result = benchmark_g2p_throughput(
            g2p_cutlet,
            sample_words[: min(1000, len(sample_words))],
            name="Japanese - G2P Throughput (cutlet)",
        )
        results.append(result)
        if verbose:
            print(result)

    except ImportError as e:
        print(f"Cutlet backend not available: {e}")
    except Exception as e:
        print(f"Failed to initialize cutlet backend: {e}")

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

    parser = argparse.ArgumentParser(description="Run kokorog2p Japanese benchmarks")
    parser.add_argument(
        "--sample-size",
        "-n",
        type=int,
        default=5000,
        help="Number of words to sample (default: 5000)",
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

    # Return non-zero if any benchmark has <90% accuracy
    critical_benchmarks = [
        r for r in results if "Validation" in r.name or "Encoding" in r.name
    ]
    if any(r.accuracy_percent < 90 for r in critical_benchmarks):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
