#!/usr/bin/env python3
"""Throughput and coverage benchmarks for Japanese G2P."""

from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from benchmarks.benchmark_ja_comparison import dependency_metadata


@dataclass
class BenchmarkResult:
    """A benchmark result with coverage terminology, not pronunciation accuracy."""

    name: str
    total_words: int
    successful: int
    failed: int
    total_time_ms: float
    words_per_second: float
    coverage_rate: float
    dependency_metadata: dict[str, str | None]
    errors: list[tuple[str, str, str]] = field(default_factory=list)

    def __str__(self) -> str:
        return (
            f"\n{'=' * 60}\n"
            f"Benchmark: {self.name}\n"
            f"{'=' * 60}\n"
            f"Total items:      {self.total_words:,}\n"
            f"Successful:       {self.successful:,}\n"
            f"Failed:           {self.failed:,}\n"
            f"Coverage:         {self.coverage_rate:.2f}%\n"
            f"Total time:       {self.total_time_ms:.2f} ms\n"
            f"Items/second:     {self.words_per_second:,.0f}\n"
        )


def load_word_list(path: Path) -> list[str]:
    """Load one Japanese word per line."""
    with path.open(encoding="utf-8") as file:
        return [line.strip() for line in file if line.strip()]


def _result(
    name: str,
    total: int,
    successful: int,
    elapsed_ms: float,
    errors: list[tuple[str, str, str]],
    *,
    backend: str = "pyopenjtalk",
) -> BenchmarkResult:
    return BenchmarkResult(
        name=name,
        total_words=total,
        successful=successful,
        failed=total - successful,
        total_time_ms=elapsed_ms,
        words_per_second=(total / (elapsed_ms / 1000)) if elapsed_ms else 0,
        coverage_rate=(successful / total * 100) if total else 0,
        dependency_metadata=dependency_metadata(backend),
        errors=errors,
    )


def benchmark_g2p_throughput(
    g2p, words: list[str], name: str = "G2P Throughput"
) -> BenchmarkResult:
    """Measure warm G2P conversion coverage and throughput."""
    if words:
        g2p(words[0])
    errors: list[tuple[str, str, str]] = []
    successful = 0
    start_time = time.perf_counter()
    for word in words:
        try:
            tokens = g2p(word)
            if tokens and any(token.phonemes for token in tokens):
                successful += 1
            elif len(errors) < 100:
                errors.append((word, "phonemes", "None"))
        except Exception as exc:
            if len(errors) < 100:
                errors.append((word, "no error", str(exc)))
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return _result(name, len(words), successful, elapsed_ms, errors)


def benchmark_sentence_throughput(
    g2p, sentences: list[str], name: str = "Sentence Throughput"
) -> BenchmarkResult:
    """Measure warm sentence conversion coverage and throughput."""
    if sentences:
        g2p(sentences[0])
    successful = 0
    start_time = time.perf_counter()
    for sentence in sentences:
        if g2p(sentence):
            successful += 1
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return _result(name, len(sentences), successful, elapsed_ms, [])


def benchmark_vocab_validation(
    g2p, words: list[str], name: str = "Vocab Validation"
) -> BenchmarkResult:
    """Measure the rate of outputs accepted by the Kokoro vocabulary."""
    from kokorog2p.vocab import validate_for_kokoro

    errors: list[tuple[str, str, str]] = []
    successful = 0
    start_time = time.perf_counter()
    for word in words:
        tokens = g2p(word)
        phonemes = "".join(token.phonemes or "" for token in tokens)
        valid, invalid = validate_for_kokoro(phonemes)
        if valid:
            successful += 1
        elif len(errors) < 100:
            errors.append((word, phonemes, f"Invalid: {invalid}"))
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return _result(name, len(words), successful, elapsed_ms, errors)


def benchmark_encoding(
    g2p, words: list[str], name: str = "Kokoro Encoding"
) -> BenchmarkResult:
    """Measure the rate of outputs that validate and encode for Kokoro."""
    from kokorog2p.vocab import encode, validate_for_kokoro

    errors: list[tuple[str, str, str]] = []
    successful = 0
    start_time = time.perf_counter()
    for word in words:
        tokens = g2p(word)
        phonemes = "".join(token.phonemes or "" for token in tokens)
        valid, invalid = validate_for_kokoro(phonemes)
        if valid and encode(phonemes):
            successful += 1
        elif len(errors) < 100:
            errors.append((word, phonemes, f"Invalid or empty encoding: {invalid}"))
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return _result(name, len(words), successful, elapsed_ms, errors)


def benchmark_phoneme_output(
    g2p, words: list[str], name: str = "Phoneme Output Sample"
) -> BenchmarkResult:
    """Collect output samples for manual pronunciation review."""
    samples = []
    start_time = time.perf_counter()
    for word in words[:100]:
        tokens = g2p(word)
        phonemes = "".join(token.phonemes or "" for token in tokens)
        samples.append((word, "", phonemes or "None"))
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    return _result(name, len(words), len(words), elapsed_ms, samples)


def run_all_benchmarks(
    sample_size: int = 5000, seed: int = 42, verbose: bool = True
) -> list[BenchmarkResult]:
    """Run Japanese benchmarks using the primary OpenJTalk backend."""
    random.seed(seed)
    sample_words = [
        "こんにちは",
        "世界",
        "今日は",
        "いい天気",
        "東京",
        "日本",
        "首都",
        "日本語",
        "勉強",
    ]
    random.seed(seed)
    random.shuffle(sample_words)
    sample_words = sample_words[:sample_size]

    from kokorog2p.ja import JapaneseG2P

    g2p = JapaneseG2P(backend="pyopenjtalk")
    results = [
        benchmark_g2p_throughput(g2p, sample_words, "Japanese G2P Throughput"),
        benchmark_vocab_validation(g2p, sample_words[:1000]),
        benchmark_encoding(g2p, sample_words[:1000]),
        benchmark_phoneme_output(g2p, sample_words),
        benchmark_sentence_throughput(
            g2p,
            [
                "こんにちは、世界。",
                "今日はいい天気ですね。",
                "東京は日本の首都です。",
                "私は日本語を勉強しています。",
            ]
            * 250,
        ),
    ]
    if verbose:
        for result in results:
            print(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run kokorog2p Japanese benchmarks")
    parser.add_argument("--sample-size", "-n", type=int, default=5000)
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument("--quiet", "-q", action="store_true")
    args = parser.parse_args()
    results = run_all_benchmarks(args.sample_size, args.seed, not args.quiet)
    critical = [
        result
        for result in results
        if "Validation" in result.name or "Encoding" in result.name
    ]
    return 0 if all(result.coverage_rate >= 90 for result in critical) else 1


if __name__ == "__main__":
    sys.exit(main())
