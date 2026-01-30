#!/usr/bin/env python3
"""Performance comparison benchmark: kokorog2p vs misaki for English (US).

This benchmark compares kokorog2p against misaki (the original Kokoro G2P library)
to measure:
- Processing speed (words/second, sentences/second)
- Memory usage
- Accuracy (phoneme-level comparison)
- Handling of edge cases (contractions, quotes, punctuation)

The benchmark uses the existing synthetic test data to ensure fair comparison
on the same input texts.

Usage:
    python benchmark_en_misaki.py
    python benchmark_en_misaki.py --num-tests 1000
    python benchmark_en_misaki.py --output results.json
    python benchmark_en_misaki.py --verbose
    python benchmark_en_misaki.py --simple
"""

import gc
import json
import sys
import time
import traceback
import tracemalloc
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.random_sentence_generator import SentenceGenerator

# =============================================================================
# Configuration & Data Structures
# =============================================================================


@dataclass
class LibraryResult:
    """Results from testing a single library."""

    library_name: str
    version: str
    total_sentences: int
    total_words: int
    total_time_seconds: float
    sentences_per_second: float
    words_per_second: float
    peak_memory_mb: float
    avg_memory_mb: float
    successful: int
    failed: int
    errors: list[dict[str, Any]]

    def to_dict(self):
        return asdict(self)


@dataclass
class PhonemeAnalysis:
    """Detailed phoneme-level analysis."""

    total_phonemes_kokoro: int
    total_phonemes_misaki: int
    phoneme_differences: dict[str, int]  # phoneme -> count of differences
    common_substitutions: list[
        tuple[str, str, int, set[str]]
    ]  # (kokoro_phoneme, misaki_phoneme, count, words)
    length_distribution: dict[str, int]  # "same", "kokoro_longer", "misaki_longer"

    def to_dict(self):
        return {
            "total_phonemes_kokoro": self.total_phonemes_kokoro,
            "total_phonemes_misaki": self.total_phonemes_misaki,
            "phoneme_differences": self.phoneme_differences,
            "common_substitutions": [
                {"kokoro": k, "misaki": m, "count": c, "words": sorted(words)}
                for k, m, c, words in self.common_substitutions[:20]
            ],
            "length_distribution": self.length_distribution,
        }


@dataclass
class ComparisonResult:
    """Comparison results between two libraries."""

    kokorog2p: LibraryResult
    misaki: LibraryResult
    speedup_factor: float  # kokorog2p speed / misaki speed
    memory_ratio: float  # kokorog2p memory / misaki memory
    agreement_rate: float  # Percentage of identical phoneme outputs
    differences: list[dict[str, Any]]  # Sample differences
    phoneme_analysis: PhonemeAnalysis  # Detailed phoneme comparison

    def to_dict(self):
        return {
            "kokorog2p": self.kokorog2p.to_dict(),
            "misaki": self.misaki.to_dict(),
            "speedup_factor": round(self.speedup_factor, 2),
            "memory_ratio": round(self.memory_ratio, 2),
            "agreement_rate": round(self.agreement_rate, 2),
            "differences_count": len(self.differences),
            "sample_differences": self.differences[:20],  # First 20 differences
            "phoneme_analysis": self.phoneme_analysis.to_dict(),
        }


# =============================================================================
# Library Wrappers
# =============================================================================


class KokoroG2PWrapper:
    """Wrapper for kokorog2p library."""

    def __init__(self, language: str = "en-us"):
        from kokorog2p.en import EnglishG2P

        self.language = language
        self.g2p = EnglishG2P(
            language=language,
            use_espeak_fallback=True,
            use_spacy=True,
        )
        self.version = self._get_version()

    def _get_version(self) -> str:
        try:
            import kokorog2p

            return getattr(kokorog2p, "__version__", "unknown")
        except Exception:
            return "unknown"

    def phonemize(self, text: str) -> tuple[str, list]:
        """Convert text to phonemes with markers.

        Returns phonemes with [markers] for tokens that have no phonetic value
        (like guillemets «», fullwidth quotes ＂, etc.) to show what was tokenized.
        Uses misaki-compatible spacing (preserves original whitespace, normalized).

        Returns:
            Tuple of (phoneme_string_with_markers, tokens)
            The phoneme string includes [markers] for debugging/comparison
        """
        tokens = self.g2p(text)
        result = []
        for token in tokens:
            if token.phonemes:
                # Regular phoneme (includes ", ❓, etc.)
                result.append(token.phonemes)
            elif token.text.strip():
                # Non-whitespace token with no phonemes (quotes like «, », ＂, etc)
                # Preserve as marker to show it was tokenized
                result.append(f"[{token.text}]")

            # ALWAYS add whitespace after token if present (even for markers)
            # This ensures proper spacing is maintained
            if token.whitespace:
                result.append(" ")

        # Join and strip trailing whitespace
        phonemes = "".join(result).strip()
        return phonemes, tokens

    def phonemize_clean(self, text: str) -> str:
        """Convert text to clean TTS-ready phonemes.

        Uses misaki-compatible spacing: preserves original whitespace
        but filters out single quote markers (❓).

        Returns:
            Clean phoneme string (no markers, only actual phonemes with natural spacing)
        """
        tokens = self.g2p(text)
        result = []
        for token in tokens:
            # Include phonemes except single quote marker
            if token.phonemes and token.phonemes != "❓":
                result.append(token.phonemes)
                # Normalize whitespace: any whitespace becomes single space
                if token.whitespace:
                    result.append(" ")

        # Join and strip trailing whitespace
        return "".join(result).strip()


class MisakiWrapper:
    """Wrapper for misaki library."""

    def __init__(self, language: str = "en-us"):
        from misaki import en, espeak

        self.language = language
        british = language == "en-gb"

        # Create fallback
        self.fallback = espeak.EspeakFallback(british=british)

        # Create G2P with espeak fallback
        self.g2p = en.G2P(trf=False, british=british, fallback=self.fallback)
        self.version = self._get_version()

    def _get_version(self) -> str:
        try:
            import misaki

            return getattr(misaki, "__version__", "unknown")
        except Exception:
            return "unknown"

    def phonemize(self, text: str) -> tuple[str, list]:
        """Convert text to phonemes.

        Returns:
            Tuple of (phoneme_string, tokens)
        """
        phonemes, tokens = self.g2p(text)
        return phonemes, tokens


# =============================================================================
# Benchmark Runner
# =============================================================================


class MisakiComparisonBenchmark:
    """Main benchmark comparing kokorog2p and misaki."""

    def __init__(
        self,
        language: str = "en-us",
        num_tests: int = 1000,
        seed: int = 42,
        verbose: bool = False,
        simple: bool = False,
    ):
        """Initialize benchmark.

        Args:
            language: Language code ('en-us' or 'en-gb').
            num_tests: Number of random tests to generate.
            seed: Random seed for reproducibility.
            verbose: Print detailed progress.
        """
        self.language = language
        self.num_tests = num_tests
        self.seed = seed
        self.verbose = verbose
        self.simple = simple

        # Generate test sentences
        print(f"Generating {num_tests} random test sentences...")
        self.generator = SentenceGenerator(seed=seed, language=language)
        self.test_cases = self.generator.generate_batch(num_tests, simple=simple)
        self.test_texts = [tc.text for tc in self.test_cases]

        # Count words
        self.total_words = sum(len(text.split()) for text in self.test_texts)

        print(f"Generated {len(self.test_texts)} sentences ({self.total_words} words)")

    @staticmethod
    def _is_word_like(text: str) -> bool:
        return any(ch.isalnum() for ch in text)

    def _build_clean_phonemes_and_word_map(
        self, tokens: list[Any]
    ) -> tuple[str, list[str]]:
        result = []
        word_map = []

        for token in tokens:
            phonemes = getattr(token, "phonemes", "")
            if not phonemes or phonemes == "❓":
                continue

            result.append(phonemes)

            token_text = getattr(token, "text", "")
            if token_text is None:
                token_text = ""
            token_text = token_text.strip().lower()

            token_phonemes = phonemes.split()
            word_map.extend([token_text] * len(token_phonemes))

            if getattr(token, "whitespace", ""):
                result.append(" ")

        return "".join(result).strip(), word_map

    def _get_word_for_phoneme_index(
        self, word_map: list[str], index: int
    ) -> str | None:
        if 0 <= index < len(word_map):
            word = word_map[index]
            if word and self._is_word_like(word):
                return word
        return None

    def benchmark_library(
        self, wrapper_class, library_name: str
    ) -> tuple[LibraryResult, list[str], list[str]]:
        """Benchmark a single library.

        Args:
            wrapper_class: Wrapper class to instantiate.
            library_name: Name of the library.

        Returns:
            Tuple of (LibraryResult, phoneme_outputs_with_markers,
                      phoneme_outputs_clean)
        """
        print(f"\n{'=' * 70}")
        print(f"Benchmarking: {library_name}")
        print(f"{'=' * 70}")

        # Initialize library
        print("Initializing...")
        wrapper = wrapper_class(language=self.language)
        print(f"Version: {wrapper.version}")

        # Warm up
        print("Warming up...")
        for text in self.test_texts[:10]:
            try:
                wrapper.phonemize(text)
            except Exception:
                pass

        # Force garbage collection
        gc.collect()

        # Start memory tracking
        tracemalloc.start()
        memory_samples = []

        # Benchmark
        print(f"Processing {len(self.test_texts)} sentences...")
        start_time = time.time()
        phoneme_outputs = []
        phoneme_outputs_clean = []
        phoneme_word_maps = []
        successful = 0
        failed = 0
        errors = []

        for i, text in enumerate(self.test_texts):
            if self.verbose and (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{len(self.test_texts)}")

            try:
                phonemes, tokens = wrapper.phonemize(text)
                phoneme_outputs.append(phonemes)

                # Get clean version for kokorog2p
                if library_name == "kokorog2p":
                    clean_phonemes, word_map = self._build_clean_phonemes_and_word_map(
                        tokens
                    )
                else:
                    if hasattr(wrapper, "phonemize_clean"):
                        clean_phonemes = wrapper.phonemize_clean(text)
                    else:
                        clean_phonemes = phonemes  # For misaki, use as-is
                    word_map = []
                phoneme_outputs_clean.append(clean_phonemes)

                if library_name == "kokorog2p":
                    phoneme_word_maps.append(word_map)

                successful += 1

                # Sample memory every 100 sentences
                if i % 100 == 0:
                    current, peak = tracemalloc.get_traced_memory()
                    memory_samples.append(current / 1024 / 1024)  # Convert to MB

            except Exception as e:
                phoneme_outputs.append("")
                phoneme_outputs_clean.append("")
                if library_name == "kokorog2p":
                    phoneme_word_maps.append([])
                failed += 1
                if len(errors) < 10:  # Keep first 10 errors
                    errors.append(
                        {
                            "sentence_id": i,
                            "text": text,
                            "error": str(e),
                            "traceback": traceback.format_exc(),
                        }
                    )

        elapsed = time.time() - start_time

        # Get final memory stats
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_memory_mb = peak_memory / 1024 / 1024
        avg_memory_mb = (
            sum(memory_samples) / len(memory_samples) if memory_samples else 0
        )

        # Calculate metrics
        sentences_per_second = len(self.test_texts) / elapsed if elapsed > 0 else 0
        words_per_second = self.total_words / elapsed if elapsed > 0 else 0

        result = LibraryResult(
            library_name=library_name,
            version=wrapper.version,
            total_sentences=len(self.test_texts),
            total_words=self.total_words,
            total_time_seconds=elapsed,
            sentences_per_second=sentences_per_second,
            words_per_second=words_per_second,
            peak_memory_mb=peak_memory_mb,
            avg_memory_mb=avg_memory_mb,
            successful=successful,
            failed=failed,
            errors=errors,
        )

        print("\nResults:")
        print(f"  Time: {elapsed:.2f}s")
        print(
            f"  Speed: {sentences_per_second:.1f} sentences/s, "
            f"{words_per_second:.1f} words/s"
        )
        print(f"  Memory: {peak_memory_mb:.1f} MB peak, {avg_memory_mb:.1f} MB avg")
        print(f"  Success: {successful}/{len(self.test_texts)}")
        if failed > 0:
            print(f"  Failed: {failed}")

        if library_name == "kokorog2p":
            self.kokoro_phoneme_word_maps = phoneme_word_maps

        return result, phoneme_outputs, phoneme_outputs_clean

    def compare_outputs(
        self, kokoro_outputs: list[str], misaki_outputs: list[str]
    ) -> tuple[float, list[dict], PhonemeAnalysis]:
        """Compare phoneme outputs from both libraries.

        Args:
            kokoro_outputs: Phoneme outputs from kokorog2p.
            misaki_outputs: Phoneme outputs from misaki.

        Returns:
            Tuple of (agreement_rate, differences, phoneme_analysis)
        """
        differences = []
        agreements = 0

        # Phoneme-level analysis
        total_phonemes_kokoro = 0
        total_phonemes_misaki = 0
        phoneme_counter_kokoro = Counter()
        phoneme_counter_misaki = Counter()
        substitutions = Counter()  # (kokoro_phoneme, misaki_phoneme) pairs
        substitution_words: dict[tuple[str, str], set[str]] = defaultdict(set)
        length_dist = {"same": 0, "kokoro_longer": 0, "misaki_longer": 0}
        word_maps = getattr(self, "kokoro_phoneme_word_maps", [])

        for i, (text, kokoro, misaki) in enumerate(
            zip(self.test_texts, kokoro_outputs, misaki_outputs, strict=False)
        ):
            word_map = word_maps[i] if i < len(word_maps) else []
            if kokoro == misaki:
                agreements += 1
            else:
                if len(differences) < 100:  # Keep first 100 differences
                    differences.append(
                        {
                            "sentence_id": i,
                            "text": text,
                            "kokorog2p": kokoro,
                            "misaki": misaki,
                            "length_diff": len(kokoro) - len(misaki),
                        }
                    )

            # Phoneme-level comparison
            kokoro_phonemes = kokoro.split()
            misaki_phonemes = misaki.split()

            total_phonemes_kokoro += len(kokoro_phonemes)
            total_phonemes_misaki += len(misaki_phonemes)

            # Count phonemes
            phoneme_counter_kokoro.update(kokoro_phonemes)
            phoneme_counter_misaki.update(misaki_phonemes)

            # Track length distribution
            if len(kokoro_phonemes) == len(misaki_phonemes):
                length_dist["same"] += 1
            elif len(kokoro_phonemes) > len(misaki_phonemes):
                length_dist["kokoro_longer"] += 1
            else:
                length_dist["misaki_longer"] += 1

            # Track substitutions (align by position for same-length outputs)
            if len(kokoro_phonemes) == len(misaki_phonemes):
                for idx, (k_ph, m_ph) in enumerate(
                    zip(kokoro_phonemes, misaki_phonemes, strict=False)
                ):
                    if k_ph != m_ph:
                        substitutions[(k_ph, m_ph)] += 1
                        word = self._get_word_for_phoneme_index(word_map, idx)
                        if word:
                            substitution_words[(k_ph, m_ph)].add(word)

        agreement_rate = (
            (agreements / len(self.test_texts)) * 100 if self.test_texts else 0
        )

        # Calculate phoneme differences
        all_phonemes = set(phoneme_counter_kokoro.keys()) | set(
            phoneme_counter_misaki.keys()
        )
        phoneme_diffs = {}
        for phoneme in all_phonemes:
            kokoro_count = phoneme_counter_kokoro.get(phoneme, 0)
            misaki_count = phoneme_counter_misaki.get(phoneme, 0)
            diff = kokoro_count - misaki_count
            if diff != 0:
                phoneme_diffs[phoneme] = diff

        # Get top substitutions with words
        common_subs = [
            (k, m, count, substitution_words.get((k, m), set()))
            for (k, m), count in substitutions.most_common(20)
        ]

        phoneme_analysis = PhonemeAnalysis(
            total_phonemes_kokoro=total_phonemes_kokoro,
            total_phonemes_misaki=total_phonemes_misaki,
            phoneme_differences=phoneme_diffs,
            common_substitutions=common_subs,
            length_distribution=length_dist,
        )

        return agreement_rate, differences, phoneme_analysis

    def run(self) -> ComparisonResult:
        """Run complete benchmark comparison.

        Returns:
            ComparisonResult with full analysis.
        """
        print(f"\n{'=' * 70}")
        print("kokorog2p vs misaki Performance Comparison")
        print(f"{'=' * 70}")
        print(f"Language: {self.language}")
        print(f"Total Tests: {self.num_tests}")
        print(f"Total Words: {self.total_words}")
        print(f"Seed: {self.seed}")
        print(f"Simple mode: {self.simple}")
        print(f"{'=' * 70}\n")

        # Benchmark kokorog2p
        kokoro_result, kokoro_outputs, kokoro_outputs_clean = self.benchmark_library(
            KokoroG2PWrapper, "kokorog2p"
        )

        # Benchmark misaki
        misaki_result, misaki_outputs, misaki_outputs_clean = self.benchmark_library(
            MisakiWrapper, "misaki"
        )

        # Compare outputs (use clean versions for comparison)
        print(f"\n{'=' * 70}")
        print("Comparing Outputs")
        print(f"{'=' * 70}")
        agreement_rate, differences, phoneme_analysis = self.compare_outputs(
            kokoro_outputs_clean, misaki_outputs_clean
        )
        print(f"Agreement rate: {agreement_rate:.2f}%")
        print(f"Differences: {len(differences)}")

        # Print phoneme analysis summary
        print("\nPhoneme Analysis:")
        print(f"  Total phonemes (kokorog2p): {phoneme_analysis.total_phonemes_kokoro}")
        print(f"  Total phonemes (misaki): {phoneme_analysis.total_phonemes_misaki}")
        print("  Length distribution:")
        for key, count in phoneme_analysis.length_distribution.items():
            print(f"    {key}: {count}")
        if phoneme_analysis.common_substitutions:
            print("  Top 5 phoneme substitutions:")
            for (
                kokoro_ph,
                misaki_ph,
                count,
                words,
            ) in phoneme_analysis.common_substitutions[:5]:
                print(f"    '{kokoro_ph}' ↔ '{misaki_ph}': {count} times")
                if words:
                    print(f"      Words: {', '.join(sorted(words))}")

        # Calculate comparison metrics
        speedup_factor = (
            kokoro_result.words_per_second / misaki_result.words_per_second
            if misaki_result.words_per_second > 0
            else 0
        )
        memory_ratio = (
            kokoro_result.peak_memory_mb / misaki_result.peak_memory_mb
            if misaki_result.peak_memory_mb > 0
            else 0
        )

        result = ComparisonResult(
            kokorog2p=kokoro_result,
            misaki=misaki_result,
            speedup_factor=speedup_factor,
            memory_ratio=memory_ratio,
            agreement_rate=agreement_rate,
            differences=differences,
            phoneme_analysis=phoneme_analysis,
        )

        # Store output versions for print_summary
        self.kokoro_outputs_with_markers = kokoro_outputs
        self.kokoro_outputs_clean = kokoro_outputs_clean

        return result

    def print_summary(self, result: ComparisonResult):
        """Print formatted comparison summary."""
        print(f"\n{'=' * 70}")
        print("COMPARISON SUMMARY")
        print(f"{'=' * 70}\n")

        print("Performance Comparison:")
        print(
            f"  kokorog2p: {result.kokorog2p.words_per_second:.1f} words/s "
            f"({result.kokorog2p.sentences_per_second:.1f} sentences/s)"
        )
        print(
            f"  misaki:    {result.misaki.words_per_second:.1f} words/s "
            f"({result.misaki.sentences_per_second:.1f} sentences/s)"
        )

        if result.speedup_factor > 1.0:
            print(f"  ⚡ kokorog2p is {result.speedup_factor:.2f}x FASTER")
        elif result.speedup_factor < 1.0:
            print(f"  ⚠️  kokorog2p is {1 / result.speedup_factor:.2f}x SLOWER")
        else:
            print(f"  ≈ Similar performance ({result.speedup_factor:.2f}x)")

        print("\nMemory Usage:")
        print(f"  kokorog2p: {result.kokorog2p.peak_memory_mb:.1f} MB peak")
        print(f"  misaki:    {result.misaki.peak_memory_mb:.1f} MB peak")

        if result.memory_ratio < 1.0:
            print(f"  💾 kokorog2p uses {result.memory_ratio:.2f}x LESS memory")
        elif result.memory_ratio > 1.0:
            print(f"  ⚠️  kokorog2p uses {result.memory_ratio:.2f}x MORE memory")
        else:
            print(f"  ≈ Similar memory usage ({result.memory_ratio:.2f}x)")

        print("\nOutput Agreement:")
        print(f"  {result.agreement_rate:.2f}% identical outputs")
        print(f"  {len(result.differences)} differences found")

        # Phoneme analysis
        pa = result.phoneme_analysis
        print("\nPhoneme-Level Analysis:")
        print("  Total phonemes:")
        print(f"    kokorog2p: {pa.total_phonemes_kokoro}")
        print(f"    misaki:    {pa.total_phonemes_misaki}")
        print("  Output length distribution:")
        total = sum(pa.length_distribution.values())
        for key, count in pa.length_distribution.items():
            pct = (count / total * 100) if total > 0 else 0
            print(f"    {key}: {count} ({pct:.1f}%)")

        if pa.common_substitutions:
            print("\n  Top 10 Phoneme Substitutions:")
            for i, (kokoro_ph, misaki_ph, count, words) in enumerate(
                pa.common_substitutions[:10], 1
            ):
                print(
                    f"    {i}. '{kokoro_ph}' (kokoro) ↔ "
                    f"'{misaki_ph}' (misaki): {count} times"
                )
                if words:
                    print(f"       Words: {', '.join(sorted(words))}")

        if result.differences:
            print("\n  Sample Differences (first 20):")

            for diff in result.differences[:20]:
                sentence_id = diff["sentence_id"]
                print(f"\n    Sentence #{sentence_id}:")
                print(f"      Text: {diff['text']}")

                # Get both versions from stored outputs
                if hasattr(self, "kokoro_outputs_with_markers"):
                    print(
                        f"      kokorog2p (with markers): "
                        f"{self.kokoro_outputs_with_markers[sentence_id]}"
                    )
                    print(
                        f"      kokorog2p (TTS-ready):    "
                        f"{self.kokoro_outputs_clean[sentence_id]}"
                    )
                else:
                    # Fallback if outputs not stored
                    print(f"      kokorog2p: {diff['kokorog2p']}")

                print(f"      misaki:                   {diff['misaki']}")

        print(f"\n{'=' * 70}\n")


# =============================================================================
# Main
# =============================================================================


def main():
    """Run benchmark with command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Performance comparison: kokorog2p vs misaki for English"
    )
    parser.add_argument(
        "--language",
        default="en-us",
        choices=["en-us", "en-gb"],
        help="Language variant to test",
    )
    parser.add_argument(
        "--num-tests",
        type=int,
        default=1000,
        help="Number of random test sentences to generate",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed progress"
    )
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use simple sentences only (no numbers, abbreviations, "
        " quotes, or variants)",
    )

    args = parser.parse_args()

    # Run benchmark
    benchmark = MisakiComparisonBenchmark(
        language=args.language,
        num_tests=args.num_tests,
        seed=args.seed,
        verbose=args.verbose,
        simple=args.simple,
    )

    result = benchmark.run()
    benchmark.print_summary(result)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
