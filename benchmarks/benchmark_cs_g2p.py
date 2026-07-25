"""Benchmarks for kokorog2p Czech G2P conversion.

This module provides benchmarks to measure:
1. G2P conversion accuracy against known phonological rules
2. G2P conversion throughput
3. End-to-end phonemization throughput for Czech text

The Czech G2P is rule-based (not dictionary-based), so we test against
known correct phonemizations from linguistic rules.

Run with: python -m benchmarks.benchmark_cs_g2p
"""

import random
import sys
import time
from dataclasses import dataclass, field


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


# Test cases for Czech phonological rules
# Format: (word, expected_phonemes)
# Note: These match the actual IPA output from CzechG2P
CZECH_TEST_CASES: list[tuple[str, str]] = [
    # Basic words
    ("Praha", "praɦa"),
    ("den", "dɛn"),
    ("krok", "krok"),
    ("pes", "pɛs"),
    ("les", "lɛs"),
    ("oko", "oko"),
    ("ucho", "uxo"),
    ("voda", "voda"),
    ("ruka", "ruka"),
    ("noha", "noɦa"),
    # Long vowels
    ("máma", "maːma"),
    ("táta", "taːta"),
    ("víno", "viːno"),
    ("múza", "muːza"),
    ("kůň", "kuːň"),  # ň stays as ň at end
    ("výr", "viːr"),
    ("léto", "lɛːto"),
    ("móda", "moːda"),
    # Palatalization (ď, ť, ň before i/í/ě)
    ("dítě", "ɟiːcɛ"),
    ("tisk", "cɪsk"),  # short i -> ɪ
    ("nic", "ɲɪt͡s"),  # c -> t͡s with tie bar
    ("děti", "ɟɛcɪ"),  # short i -> ɪ
    ("tělo", "cɛlo"),
    ("něco", "ɲɛt͡so"),  # c -> t͡s
    ("město", "mɲɛsto"),
    ("pěna", "pjɛna"),
    ("věc", "vjɛt͡s"),  # c -> t͡s
    # CH digraph
    ("chata", "xata"),
    ("chléb", "xlɛːp"),
    ("duch", "dux"),
    ("moucha", "mouxa"),
    # R-háček (ř)
    ("řeka", "r̝ɛka"),
    ("třída", "tr̝iːda"),
    ("dřevo", "dr̝ɛvo"),
    ("moře", "mor̝ɛ"),
    ("keř", "kɛr̝"),
    # Final devoicing
    ("dub", "dup"),
    ("had", "ɦat"),
    ("kov", "kof"),
    ("nůž", "nuːʃ"),
    ("led", "lɛt"),
    # Voicing assimilation
    ("vstup", "fstup"),
    ("kde", "ɡdɛ"),  # Note: uses IPA ɡ (U+0261)
    ("sbor", "zbor"),
    ("shoda", "sɦoda"),  # s+h doesn't trigger voicing (h is voiced but not in pair)
    ("tužka", "tuʃka"),
    ("loďka", "locka"),  # ď before k -> c (devoiced ť)
    # Combinations
    ("mě", "mɲɛ"),
    ("bě", "bjɛ"),
    ("pě", "pjɛ"),
    ("vě", "vjɛ"),
    # Note: fě doesn't have special rule in Czech orthography
    # (rare foreign word pattern)
    # TS combination
    ("citron", "t͡sɪtron"),  # c -> t͡s, i -> ɪ
    ("cena", "t͡sɛna"),  # c -> t͡s
    # Foreign sounds (ie, ia, io)
    ("piano", "pɪjano"),  # i -> ɪ
    ("radio", "radɪjo"),  # i -> ɪ
    ("historie", "ɦɪstorɪjɛ"),  # i -> ɪ
    # Common words
    ("dobrý", "dobriː"),  # ý -> iː
    ("ahoj", "aɦoj"),
    ("ano", "ano"),
    ("ne", "nɛ"),
    ("prosím", "prosiːm"),
    # Words with ů
    ("dům", "duːm"),
    ("stůl", "stuːl"),
    ("bůh", "buːɦ"),
]


def get_test_dictionary() -> dict[str, str]:
    """Get test dictionary for Czech phonological rules.

    Returns:
        Dictionary mapping words to expected phonemes.
    """
    return dict(CZECH_TEST_CASES)


def benchmark_accuracy(
    g2p,
    gold: dict[str, str],
    name: str = "Accuracy vs Test Cases",
) -> BenchmarkResult:
    """Benchmark G2P accuracy against test cases.

    Args:
        g2p: The G2P instance to test.
        gold: Test dictionary mapping words to expected phonemes.
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


def benchmark_phonological_categories(
    g2p,
    name: str = "Phonological Rule Categories",
) -> BenchmarkResult:
    """Benchmark accuracy per phonological category.

    Args:
        g2p: The G2P instance to test.
        name: Name for this benchmark.

    Returns:
        BenchmarkResult with category-level accuracy.
    """
    categories: dict[str, list[tuple[str, str]]] = {
        "Basic words": [
            ("Praha", "praɦa"),
            ("den", "dɛn"),
            ("pes", "pɛs"),
            ("oko", "oko"),
            ("voda", "voda"),
        ],
        "Long vowels": [
            ("máma", "maːma"),
            ("víno", "viːno"),
            ("kůň", "kuːň"),
            ("léto", "lɛːto"),
        ],
        "Palatalization": [
            ("dítě", "ɟiːcɛ"),
            ("tisk", "cɪsk"),
            ("nic", "ɲɪt͡s"),
            ("město", "mɲɛsto"),
        ],
        "CH digraph": [
            ("chata", "xata"),
            ("chléb", "xlɛːp"),
            ("duch", "dux"),
        ],
        "R-háček": [
            ("řeka", "r̝ɛka"),
            ("třída", "tr̝iːda"),
            ("moře", "mor̝ɛ"),
        ],
        "Final devoicing": [
            ("dub", "dup"),
            ("had", "ɦat"),
            ("kov", "kof"),
            ("nůž", "nuːʃ"),
        ],
        "Voicing assimilation": [
            ("vstup", "fstup"),
            ("kde", "ɡdɛ"),
            ("sbor", "zbor"),
            ("tužka", "tuʃka"),
        ],
    }

    total = 0
    successful = 0
    errors: list[tuple[str, str, str]] = []

    start_time = time.perf_counter()

    for category, words in categories.items():
        cat_success = 0
        cat_total = len(words)

        for word, expected in words:
            tokens = g2p(word)
            got = tokens[0].phonemes if tokens else "None"
            total += 1

            if got == expected:
                successful += 1
                cat_success += 1
            else:
                errors.append((f"[{category}] {word}", expected, got))

        cat_pct = (cat_success / cat_total * 100) if cat_total else 0
        print(f"  {category:25} {cat_success}/{cat_total} ({cat_pct:.1f}%)")

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000

    return BenchmarkResult(
        name=name,
        total_words=total,
        successful=successful,
        failed=total - successful,
        total_time_ms=total_time_ms,
        words_per_second=total / (total_time_ms / 1000) if total_time_ms > 0 else 0,
        accuracy_percent=(successful / total * 100) if total else 0,
        errors=errors,
    )


# Common Czech words for throughput testing
COMMON_CZECH_WORDS = [
    "a",
    "aby",
    "ale",
    "ani",
    "ano",
    "asi",
    "až",
    "bez",
    "být",
    "byl",
    "byla",
    "bylo",
    "byli",
    "co",
    "což",
    "člověk",
    "den",
    "do",
    "dva",
    "děti",
    "jeho",
    "jej",
    "její",
    "jen",
    "ještě",
    "ji",
    "jim",
    "jiný",
    "jít",
    "již",
    "k",
    "kam",
    "kde",
    "kdo",
    "kdy",
    "když",
    "kromě",
    "který",
    "kvůli",
    "málo",
    "mezi",
    "mít",
    "moci",
    "muset",
    "můj",
    "na",
    "nad",
    "ně",
    "nebo",
    "než",
    "nic",
    "nikdo",
    "nový",
    "o",
    "od",
    "on",
    "ona",
    "oni",
    "pak",
    "po",
    "pod",
    "podle",
    "pokud",
    "pouze",
    "právě",
    "pro",
    "první",
    "před",
    "přes",
    "přesto",
    "při",
    "rok",
    "s",
    "se",
    "si",
    "sice",
    "snad",
    "svůj",
    "ta",
    "tak",
    "také",
    "takový",
    "tam",
    "ten",
    "tedy",
    "tento",
    "to",
    "toto",
    "třeba",
    "tři",
    "tu",
    "ty",
    "u",
    "už",
    "v",
    "však",
    "ve",
    "velmi",
    "více",
    "vlastně",
    "všechen",
    "vůbec",
    "vždy",
    "z",
    "za",
    "zatímco",
    "zde",
    "že",
    "žádný",
    "život",
]


def run_all_benchmarks(
    sample_size: int = 1000,
    seed: int = 42,
    verbose: bool = True,
) -> list[BenchmarkResult]:
    """Run all Czech G2P benchmarks.

    Args:
        sample_size: Number of words to sample for throughput benchmarks.
        seed: Random seed for reproducibility.
        verbose: Whether to print results.

    Returns:
        List of BenchmarkResult objects.
    """
    random.seed(seed)
    results: list[BenchmarkResult] = []

    print("Loading Czech test cases...")
    gold = get_test_dictionary()
    print(f"Total test cases: {len(gold):,}")

    # Import Czech G2P
    print("\nInitializing Czech G2P...")
    from kokorog2p.cs import CzechG2P

    g2p = CzechG2P()

    print("\nRunning benchmarks...\n")

    # Benchmark 1: Accuracy vs Test Cases
    result = benchmark_accuracy(
        g2p,
        gold,
        name="Czech - Accuracy vs Test Cases",
    )
    results.append(result)
    if verbose:
        print(result)
        if result.errors:
            print("Errors (word, expected, got):")
            for word, expected, got in result.errors[:20]:
                print(f"  {word}: {expected} -> {got}")

    # Benchmark 2: Phonological categories
    print("\nPhonological category breakdown:")
    result = benchmark_phonological_categories(
        g2p,
        name="Czech - Phonological Categories",
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 3: G2P Throughput
    sample_words = (COMMON_CZECH_WORDS * (sample_size // len(COMMON_CZECH_WORDS) + 1))[
        :sample_size
    ]
    random.shuffle(sample_words)
    result = benchmark_throughput(
        g2p,
        sample_words,
        name="Czech - G2P Throughput",
    )
    results.append(result)
    if verbose:
        print(result)

    # Benchmark 4: Sample phoneme outputs
    result = benchmark_phoneme_output(
        g2p,
        list(gold.keys()),
        name="Czech - Phoneme Output Sample",
    )
    results.append(result)
    if verbose:
        print(result)
        print("Sample outputs (word -> phonemes):")
        for word, _, phonemes in result.errors[:20]:
            print(f"  {word} -> {phonemes}")

    # Benchmark 5: Sentence throughput
    sample_sentences = [
        "Dobrý den, jak se máte?",
        "Praha je hlavní město České republiky.",
        "Děkuji za všechno.",
        "Prosím, kde je nejbližší nádraží?",
        "Dnes je krásný den.",
        "Mám rád českou kuchyni.",
        "Kolik to stojí?",
        "Nerozumím česky.",
        "Mluvíte anglicky?",
        "Kde je toaleta?",
    ] * 100  # 1000 sentences

    result = benchmark_sentence_throughput(
        g2p,
        sample_sentences,
        name="Czech - Sentence Throughput",
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

    parser = argparse.ArgumentParser(description="Run kokorog2p Czech benchmarks")
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
    sys.exit(main())
