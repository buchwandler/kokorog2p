"""Benchmarks for kokorog2p G2P conversion.

This module provides benchmarks to measure:
1. Dictionary lookup speed
2. G2P conversion accuracy (comparing output to dictionary)
3. Vocabulary coverage validation
4. End-to-end phonemization throughput

Run with: python -m kokorog2p.benchmarks.benchmark_g2p
"""

import json
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


def load_dictionary(path: Path) -> dict[str, str]:
    """Load a dictionary JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    # Filter out dict entries (heteronyms) - keep only simple str -> str mappings
    return {k: v for k, v in data.items() if isinstance(v, str)}


def benchmark_dictionary_lookup(
    dictionary: dict[str, str],
    words: list[str],
    name: str = "Dictionary Lookup",
) -> BenchmarkResult:
    """Benchmark direct dictionary lookup speed.

    Args:
        dictionary: The dictionary to test (gold or silver).
        words: List of words to look up.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with timing data.
    """
    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words:
        ps = dictionary.get(word)
        if ps is not None:
            successful += 1
        else:
            failed += 1
            if len(errors) < 100:  # Limit error collection
                errors.append((word, "expected", "None"))

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


def benchmark_g2p_conversion(
    g2p,
    words: list[str],
    expected: dict[str, str],
    name: str = "G2P Conversion",
) -> BenchmarkResult:
    """Benchmark full G2P conversion speed and accuracy.

    Args:
        g2p: The G2P instance to test.
        words: List of words to convert.
        expected: Dictionary of expected phonemes.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with timing and accuracy data.
    """
    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words:
        tokens = g2p(word)
        ps = tokens[0].phonemes if tokens else None
        expected_ps = expected.get(word)

        if ps == expected_ps:
            successful += 1
        else:
            failed += 1
            if len(errors) < 100:
                errors.append((word, expected_ps or "None", ps or "None"))

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
    total_words = 0

    start_time = time.perf_counter()

    for sentence in sentences:
        tokens = g2p(sentence)
        total_words += len([t for t in tokens if t.is_word])

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=total_words,
        successful=total_words,
        failed=0,
        total_time_ms=total_time_ms,
        words_per_second=total_words / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=100.0,  # No accuracy check for throughput
    )


def benchmark_vocab_validation(
    phonemes_dict: dict[str, str],
    vocab: frozenset,
    name: str = "Vocab Validation",
) -> BenchmarkResult:
    """Validate that all phonemes in dictionary are in vocabulary.

    Args:
        phonemes_dict: Dictionary of word -> phonemes.
        vocab: Set of valid phoneme characters.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with validation data.
    """
    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word, ps in phonemes_dict.items():
        invalid_chars = [c for c in ps if c not in vocab]
        if not invalid_chars:
            successful += 1
        else:
            failed += 1
            if len(errors) < 100:
                errors.append((word, ps, f"Invalid: {invalid_chars}"))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=len(phonemes_dict),
        successful=successful,
        failed=failed,
        total_time_ms=total_time_ms,
        words_per_second=len(phonemes_dict) / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=(successful / len(phonemes_dict) * 100)
        if phonemes_dict
        else 0,
        errors=errors,
    )


def benchmark_encoding(
    phonemes_dict: dict[str, str],
    name: str = "Vocab Encoding",
) -> BenchmarkResult:
    """Benchmark phoneme-to-token encoding speed.

    Args:
        phonemes_dict: Dictionary of word -> phonemes.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with timing and validation data.
    """
    from kokorog2p.vocab import encode, validate_for_kokoro

    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word, ps in phonemes_dict.items():
        is_valid, invalid = validate_for_kokoro(ps)
        if is_valid:
            ids = encode(ps)
            if ids:  # Non-empty encoding
                successful += 1
            else:
                failed += 1
                if len(errors) < 100:
                    errors.append((word, ps, "Empty encoding"))
        else:
            failed += 1
            if len(errors) < 100:
                errors.append((word, ps, f"Invalid chars: {invalid}"))

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=len(phonemes_dict),
        successful=successful,
        failed=failed,
        total_time_ms=total_time_ms,
        words_per_second=len(phonemes_dict) / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
        accuracy_percent=(successful / len(phonemes_dict) * 100)
        if phonemes_dict
        else 0,
        errors=errors,
    )


def benchmark_backend_accuracy(
    backend,
    words: list[str],
    expected: dict[str, str],
    name: str = "Backend Accuracy",
    is_fallback: bool = True,
) -> BenchmarkResult:
    """Benchmark backend accuracy against dictionary.

    This tests backend phonemization WITHOUT using the gold/silver dictionaries,
    comparing the backend output directly against the expected dictionary values.

    Args:
        backend: The backend instance to test (EspeakFallback, GoruutBackend, etc.).
        words: List of words to convert.
        expected: Dictionary of expected phonemes (gold or silver).
        name: Name for this benchmark.
        is_fallback: If True, backend returns (phonemes, rating) tuple when called.
                    If False, backend has word_phonemes() method.

    Returns:
        BenchmarkResult with timing and accuracy data.
    """
    successful = 0
    failed = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for word in words:
        if is_fallback:
            # Fallback-style: callable returning (phonemes, rating)
            ps, _rating = backend(word)
        else:
            # Backend-style: has word_phonemes() method
            ps = backend.word_phonemes(word)

        expected_ps = expected.get(word)

        if ps == expected_ps:
            successful += 1
        else:
            failed += 1
            if len(errors) < 100:
                errors.append((word, expected_ps or "None", ps or "None"))

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


class TorchFallback:
    """BART-based neural G2P fallback model.

    This is a standalone implementation for benchmarking, based on the
    FallbackNetwork from misaki.
    """

    def __init__(self, british: bool = False):
        """Initialize the torch fallback.

        Args:
            british: Whether to use British English model.
        """
        try:
            import torch
            from transformers import BartForConditionalGeneration
        except ImportError as e:
            raise ImportError(
                "torch and transformers are required for TorchFallback. "
                "Install with: pip install torch transformers"
            ) from e

        self.british = british
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_name = "PeterReid/graphemes_to_phonemes_en_" + ("gb" if british else "us")
        self.model = BartForConditionalGeneration.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        self.grapheme_to_token = {
            g: i for i, g in enumerate(self.model.config.grapheme_chars)
        }
        self.token_to_phoneme = dict(enumerate(self.model.config.phoneme_chars))
        self._torch = torch

    def graphemes_to_tokens(self, graphemes: str) -> list[int]:
        """Convert graphemes to token IDs."""
        return [1] + [self.grapheme_to_token.get(g, 3) for g in graphemes] + [2]

    def tokens_to_phonemes(self, tokens: list[int]) -> str:
        """Convert token IDs to phoneme string."""
        return "".join([self.token_to_phoneme.get(t, "") for t in tokens if t > 3])

    def __call__(self, word: str) -> tuple[str, int]:
        """Convert a word to phonemes.

        Args:
            word: The word to convert.

        Returns:
            Tuple of (phonemes, rating).
        """
        input_ids = self._torch.tensor(
            [self.graphemes_to_tokens(word)], device=self.device
        )

        with self._torch.no_grad():
            generated_ids = self.model.generate(input_ids=input_ids)
        output_text = self.tokens_to_phonemes(generated_ids[0].tolist())
        return (output_text, 1)


def _print_result_with_errors(result: BenchmarkResult, verbose: bool) -> None:
    """Print benchmark result with sample errors if verbose."""
    if verbose:
        print(result)
        if result.errors:
            print("Sample errors (word, expected, got):")
            for word, expected_val, got in result.errors[:10]:
                print(f"  {word}: {expected_val} -> {got}")


def _print_summary(results: list[BenchmarkResult]) -> None:
    """Print benchmark summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in results:
        print(
            f"{r.name:40} | {r.accuracy_percent:6.2f}% "
            f"| {r.words_per_second:10,.0f} words/sec"
        )


def run_all_benchmarks(
    sample_size: int = 10000,
    seed: int = 42,
    verbose: bool = True,
) -> list[BenchmarkResult]:
    """Run all benchmarks.

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
    data_dir = Path(__file__).parent.parent / "kokorog2p" / "en" / "data"
    if not data_dir.exists():
        # Try relative to current file
        data_dir = Path(__file__).parent.parent / "en" / "data"

    print(f"Loading dictionaries from {data_dir}...")

    # Load US dictionaries
    us_gold = load_dictionary(data_dir / "us_gold.json")
    us_silver = load_dictionary(data_dir / "us_silver.json")

    print(f"US Gold: {len(us_gold):,} entries")
    print(f"US Silver: {len(us_silver):,} entries")

    # Sample words
    us_gold_words = random.sample(list(us_gold.keys()), min(sample_size, len(us_gold)))
    us_silver_words = random.sample(
        list(us_silver.keys()), min(sample_size, len(us_silver))
    )

    # Import kokorog2p components
    print("\nInitializing G2P components...")
    from kokorog2p.en import EnglishG2P
    from kokorog2p.en.fallback import EspeakFallback
    from kokorog2p.phonemes import US_VOCAB

    g2p_no_spacy = EnglishG2P(
        language="en-us", use_espeak_fallback=False, use_spacy=False
    )

    # Initialize espeak fallback for accuracy testing (without dictionary)
    espeak_fallback = EspeakFallback(british=False)

    # Try to initialize goruut backend (optional)
    goruut_backend = None
    try:
        from kokorog2p.backends.goruut import GoruutBackend

        if GoruutBackend.is_available():
            goruut_backend = GoruutBackend(language="en-us")
            print("Goruut backend loaded successfully.")
        else:
            print("Goruut backend not available (pygoruut not installed).")
    except ImportError as e:
        print(f"Goruut backend not available: {e}")

    # Try to initialize torch fallback (optional)
    torch_fallback = None
    try:
        print("Loading BART model for torch fallback...")
        # torch_fallback = TorchFallback(british=False)
        print("Torch fallback loaded successfully.")
    except ImportError as e:
        print(f"Torch fallback not available: {e}")
    except Exception as e:
        print(f"Failed to load torch fallback: {e}")

    print("\nRunning benchmarks...\n")

    # Benchmark 1: Espeak accuracy on gold dictionary (no dictionary lookup)
    result = benchmark_backend_accuracy(
        espeak_fallback,
        us_gold_words[: min(1000, len(us_gold_words))],
        us_gold,
        name="US Gold - Espeak Only Accuracy",
        is_fallback=True,
    )
    results.append(result)
    _print_result_with_errors(result, verbose)

    # Benchmark 2: Espeak accuracy on silver dictionary (no dictionary lookup)
    result = benchmark_backend_accuracy(
        espeak_fallback,
        us_silver_words[: min(1000, len(us_silver_words))],
        us_silver,
        name="US Silver - Espeak Only Accuracy",
        is_fallback=True,
    )
    results.append(result)
    _print_result_with_errors(result, verbose)

    # Benchmark 3: Torch fallback accuracy on gold dictionary (if available)
    if torch_fallback is not None:
        result = benchmark_backend_accuracy(
            torch_fallback,
            us_gold_words[: min(1000, len(us_gold_words))],
            us_gold,
            name="US Gold - Torch Only Accuracy",
            is_fallback=True,
        )
        results.append(result)
        _print_result_with_errors(result, verbose)

        # Benchmark 4: Torch fallback accuracy on silver dictionary
        result = benchmark_backend_accuracy(
            torch_fallback,
            us_silver_words[: min(1000, len(us_silver_words))],
            us_silver,
            name="US Silver - Torch Only Accuracy",
            is_fallback=True,
        )
        results.append(result)
        _print_result_with_errors(result, verbose)

    # Benchmark 5: Goruut accuracy on gold dictionary (if available)
    if goruut_backend is not None:
        result = benchmark_backend_accuracy(
            goruut_backend,
            us_gold_words[: min(1000, len(us_gold_words))],
            us_gold,
            name="US Gold - Goruut Only Accuracy",
            is_fallback=False,
        )
        results.append(result)
        _print_result_with_errors(result, verbose)

        # Benchmark 6: Goruut accuracy on silver dictionary
        result = benchmark_backend_accuracy(
            goruut_backend,
            us_silver_words[: min(1000, len(us_silver_words))],
            us_silver,
            name="US Silver - Goruut Only Accuracy",
            is_fallback=False,
        )
        results.append(result)
        _print_result_with_errors(result, verbose)

    # Benchmark 7: Full G2P on gold dictionary (with dictionary, without spaCy)
    result = benchmark_g2p_conversion(
        g2p_no_spacy,
        us_gold_words[: min(1000, len(us_gold_words))],
        us_gold,
        name="US Gold - G2P (no spaCy)",
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 8: Vocabulary validation
    result = benchmark_vocab_validation(
        us_gold, US_VOCAB, name="US Gold - Vocab Validation"
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 9: Encoding validation
    result = benchmark_encoding(
        {k: us_gold[k] for k in us_gold_words}, name="US Gold - Kokoro Encoding"
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 10: Sentence throughput (espeak backend)
    sample_sentences = [
        "The quick brown fox jumps over the lazy dog.",
        "Hello world, how are you doing today?",
        "This is a test of the text to speech system.",
        "Natural language processing is fascinating.",
        "The weather today is sunny with a chance of rain.",
    ] * 200  # 1000 sentences

    result = benchmark_sentence_throughput(
        g2p_no_spacy, sample_sentences, name="Sentence Throughput (espeak, no spaCy)"
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 11: Sentence throughput with goruut backend (if available)
    if goruut_backend is not None:
        from kokorog2p.goruut_g2p import GoruutOnlyG2P

        g2p_goruut = GoruutOnlyG2P(language="en-us")

        result = benchmark_sentence_throughput(
            g2p_goruut, sample_sentences, name="Sentence Throughput (goruut, no spaCy)"
        )
        results.append(result)
        if verbose:
            print(result)

    # Summary
    if verbose:
        _print_summary(results)

    return results


def main():
    """Run benchmarks from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run kokorog2p benchmarks")
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

    # Return non-zero if any benchmark has <95% accuracy
    critical_benchmarks = [
        r for r in results if "Validation" in r.name or "Encoding" in r.name
    ]
    if any(r.accuracy_percent < 95 for r in critical_benchmarks):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
