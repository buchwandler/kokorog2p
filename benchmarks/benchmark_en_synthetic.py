#!/usr/bin/env python3
"""Benchmark for English quotes, contractions, and punctuation handling.

This benchmark systematically tests the English G2P system's ability to handle:
- Different apostrophe variants in contractions (including rare Unicode variants)
- Different quote character combinations
- All punctuation marks from Kokoro vocab
- Mixed combinations

The benchmark generates random test sentences and validates that the
G2P produces
consistent, correct output. It reports failures categorized by type.
"""

import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.random_sentence_generator import SentenceGenerator, TestCase
from kokorog2p.en import EnglishG2P

# =============================================================================
# Result Data Structures
# =============================================================================


@dataclass
class TestResult:
    """Result from testing a single test case."""

    test_id: int
    text: str
    category: str
    params: dict[str, Any]
    expected_phonemes: str
    actual_phonemes: str
    passed: bool
    failure_type: str | None = None

    def to_dict(self):
        return asdict(self)


@dataclass
class CategoryStats:
    """Statistics for a test category."""

    total: int = 0
    passed: int = 0
    failed: int = 0

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total * 100) if self.total > 0 else 0.0

    def to_dict(self):
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "pass_rate": round(self.pass_rate, 2),
        }


@dataclass
class BenchmarkResults:
    """Overall benchmark results."""

    metadata: dict[str, Any]
    category_stats: dict[str, CategoryStats]
    failures: list[TestResult]
    failure_analysis: dict[str, Any]

    def to_dict(self):
        return {
            "metadata": self.metadata,
            "category_stats": {k: v.to_dict() for k, v in self.category_stats.items()},
            "failures": [f.to_dict() for f in self.failures],
            "failure_analysis": self.failure_analysis,
        }


# =============================================================================
# Failure Analyzer
# =============================================================================


class FailureAnalyzer:
    """Analyzes failures to categorize and identify patterns."""

    def __init__(self):
        self.failures_by_category = defaultdict(list)
        self.failures_by_type = defaultdict(int)
        self.failures_by_apostrophe = defaultdict(int)
        self.failures_by_quote = defaultdict(int)
        self.failures_by_punct = defaultdict(int)

    def analyze_failure(self, test_case: TestCase, expected: str, actual: str) -> str:
        """Determine failure type.

        Returns:
            Failure type string.
        """
        # Check for split contraction (contraction appears separated)
        text = test_case.text.lower()
        if "'" in text or "'" in text or "`" in text or "´" in text:
            # Check if a contraction was split
            for word in text.split():
                if any(c in word for c in ["'", "'", "`", "´"]):
                    # This word should be a contraction
                    # If it appears split in phonemes, that's an issue
                    if len(actual.split()) > len(expected.split()) + 2:
                        return "split_contraction"

        # Check for lost punctuation
        punct_chars = set(';:,.!?—…"""()')
        expected_puncts = [c for c in expected if c in punct_chars]
        actual_puncts = [c for c in actual if c in punct_chars]
        if len(expected_puncts) != len(actual_puncts):
            return "lost_punctuation"

        # Check for phoneme mismatch (different phonemes but same structure)
        if len(expected.split()) == len(actual.split()):
            return "phoneme_mismatch"

        # Check for tokenization error (different number of tokens)
        if len(expected.split()) != len(actual.split()):
            return "tokenization_error"

        return "unknown"

    def record_failure(self, result: TestResult) -> None:
        """Record a failure for analysis."""
        self.failures_by_category[result.category].append(result)
        self.failures_by_type[result.failure_type or "unknown"] += 1

        # Track by specific parameters
        if "apostrophe_type" in result.params:
            self.failures_by_apostrophe[result.params["apostrophe_type"]] += 1
        if "quote_type" in result.params:
            self.failures_by_quote[result.params["quote_type"]] += 1
        if "punctuation" in result.params:
            punct = result.params["punctuation"]
            if isinstance(punct, str) and len(punct) <= 3:
                self.failures_by_punct[punct] += 1

    def generate_analysis(self) -> dict[str, Any]:
        """Generate failure analysis report."""
        return {
            "by_category": {k: len(v) for k, v in self.failures_by_category.items()},
            "by_failure_type": dict(self.failures_by_type),
            "by_apostrophe_type": dict(self.failures_by_apostrophe),
            "by_quote_type": dict(self.failures_by_quote),
            "by_punctuation": dict(self.failures_by_punct),
        }


# =============================================================================
# Benchmark Runner
# =============================================================================


class QuotesContractionsBenchmark:
    """Main benchmark runner for quotes, contractions, and punctuation."""

    def __init__(
        self,
        language: str = "en-us",
        num_tests: int = 1000,
        seed: int = 42,
        verbose: bool = False,
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

        # Initialize components
        # G2P for testing and generating expected phonemes
        print(f"Initializing G2P for {language} (with spaCy)...")
        self.g2p_test = EnglishG2P(
            language=language, use_espeak_fallback=True, use_spacy=True
        )

        # Generator with G2P to generate expected phonemes
        self.generator = SentenceGenerator(seed=seed, g2p=self.g2p_test)

        # Results tracking
        self.results: list[TestResult] = []
        self.category_stats: dict[str, CategoryStats] = defaultdict(CategoryStats)
        self.analyzer = FailureAnalyzer()

    def validate_output(self, test_case: TestCase, phonemes: str) -> tuple[bool, str]:
        """Validate phoneme output against ground truth expectations.

        Args:
            test_case: The test case
            phonemes: The generated phonemes

        Returns:
            Tuple of (passed, expected_description)
        """
        import re

        text = test_case.text
        issues = []

        # Rule 1: Contractions should NOT be split into individual letters
        # Examples: don't → dˈOnt (GOOD), not dˈi ˈO ˈɛn tˈi (BAD - spelled out)
        contraction_chars = ["'", "'", "`", "´", "ʹ", "ʻ", "ʼ", "ʽ"]
        for word in text.split():
            # Check if word contains a contraction character
            if any(char in word for char in contraction_chars):
                # Common patterns for spelled-out letters (indicates the contraction
                # was not recognized and letters were spelled individually)
                spelled_patterns = [
                    # "d o n t" pattern
                    "dˈi ˈO ˈɛn",  # "d o n"
                    # Single letter spellings (with spaces around to
                    # avoid false positives)
                    " tˈi ",  # " t " (standalone)
                    " ˈɛs ",  # " s "
                    " ˈɛm ",  # " m "
                    " ˈɑɹ ",  # " r "
                    " ˈvi ",  # " v "
                    " ˈɛl ",  # " l "
                    # Common contraction parts spelled out
                    "ˈɑɹ ˈi",  # "r e" (from "you're", "we're")
                    "ˈɛl ˈɛl",  # "l l" (from "I'll", "we'll")
                ]
                for pattern in spelled_patterns:
                    if pattern in phonemes:
                        issues.append(
                            f"Contraction '{word}' may be spelled out "
                            f"(found pattern: {pattern.strip()})"
                        )
                        break

        # Rule 2: Quote-like characters should be converted to curly quotes
        # We need to distinguish between quotes and contractions.
        # Backtick/acute inside words (\w`\w) = contraction, otherwise = quote
        quote_chars_in_text = ['"', "«", "»", "‹", "›"]
        has_quotes = any(char in text for char in quote_chars_in_text)

        # Check for standalone backticks/acutes (used as quotes, not contractions)
        # Standalone = present but NOT between word characters
        has_backtick = "`" in text
        has_acute = "´" in text
        backtick_in_contraction = bool(re.search(r"\w`\w", text))
        acute_in_contraction = bool(re.search(r"\w´\w", text))

        standalone_backtick = has_backtick and not backtick_in_contraction
        standalone_acute = has_acute and not acute_in_contraction

        if has_quotes or standalone_backtick or standalone_acute:
            # Should have curly quotes in output
            if "\u201c" not in phonemes and "\u201d" not in phonemes:
                issues.append(
                    'Quotes should be converted to curly quotes ("\u201c \u201d)'
                )

        # Rule 3: No straight quotes in output (should be curly)
        if '"' in phonemes:
            issues.append(
                'Output contains straight quotes ("), should be curly ("\u201c \u201d)'
            )

        # Rule 4: No guillemets or other quote variants in output
        if any(char in phonemes for char in ["«", "»", "‹", "›"]):
            issues.append(
                "Output contains guillemets (« »), "
                'should be curly quotes ("\u201c \u201d)'
            )

        if issues:
            return False, "; ".join(issues)
        return True, "OK"

    def generate_expected_phonemes(self, text: str) -> str:
        """Generate description of expected output.

        This is NOT generating phonemes, but rather a description
        of what the output should satisfy.
        """
        return "Valid phonemes with correct quote/contraction handling"

    def test_case(self, test_id: int, test_case: TestCase) -> TestResult:
        """Test a single case.

        Args:
            test_id: Test identifier.
            test_case: TestCase to test.

        Returns:
            TestResult.
        """
        import re

        # Run G2P
        tokens = self.g2p_test(test_case.text)

        # Join phonemes and format them (remove spaces around punctuation/quotes)
        actual = " ".join(t.phonemes for t in tokens if t.phonemes)

        # Remove spaces around punctuation
        actual = actual.replace(" , ", ",").replace(" .", ".")
        actual = actual.replace(" !", "!").replace(" ?", "?")
        actual = actual.replace(" ;", ";").replace(" :", ":")
        actual = actual.replace(" …", "…").replace(" … ", "…").replace("… ", "…")
        actual = actual.replace(" — ", "—").replace(" – ", "–")
        actual = actual.replace(" —", "—").replace(" –", "–")
        actual = actual.replace("— ", "—").replace("– ", "–")

        # Remove spaces after opening quotes and before closing quotes (all types)
        # Remove space after any quote-like character
        actual = re.sub(
            r'(["\'\u201c\u201d\u2018\u2019\u201a\u201e«»「」＂″‚„]) ',
            r"\1",
            actual,
        )
        # Remove space before any quote-like character
        actual = re.sub(
            r' (["\'\u201c\u201d\u2018\u2019\u201a\u201e«»「」＂″‚„])',
            r"\1",
            actual,
        )

        # Compare against expected phonemes from test case
        expected = test_case.expected_phonemes
        passed = (actual == expected) if expected else False

        # Also validate against rules for additional checking
        rule_passed, validation_msg = self.validate_output(test_case, actual)

        # A test passes only if both phoneme match AND rules pass
        if not rule_passed:
            passed = False

        failure_type = None
        if not passed:
            failure_type = self.analyzer.analyze_failure(test_case, expected, actual)

        result = TestResult(
            test_id=test_id,
            text=test_case.text,
            category=test_case.category,
            params=test_case.params,
            expected_phonemes=expected,
            actual_phonemes=actual,
            passed=passed,
            failure_type=failure_type,
        )

        return result

    def run(self) -> BenchmarkResults:
        """Run complete benchmark.

        Returns:
            BenchmarkResults with full analysis.
        """
        print(f"\n{'=' * 70}")
        print("English Quotes/Contractions/Punctuation Benchmark")
        print(f"{'=' * 70}")
        print(f"Language: {self.language}")
        print(f"Total Tests: {self.num_tests}")
        print(f"Seed: {self.seed}")
        print(f"{'=' * 70}\n")

        # Generate test cases
        print("Generating random test cases...")
        test_cases = self.generator.generate_batch(self.num_tests)
        print(f"Generated {len(test_cases)} test cases\n")

        # Show distribution
        dist = Counter(t.category for t in test_cases)
        print("Test distribution:")
        for category, count in sorted(dist.items()):
            print(f"  {category}: {count}")
        print()

        # Run tests
        print("Running tests...")
        start_time = time.time()

        for i, test_case in enumerate(test_cases):
            if self.verbose and (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{len(test_cases)}")

            result = self.test_case(i + 1, test_case)
            self.results.append(result)

            # Update stats
            stats = self.category_stats[result.category]
            stats.total += 1
            if result.passed:
                stats.passed += 1
            else:
                stats.failed += 1
                self.analyzer.record_failure(result)

        elapsed = time.time() - start_time
        print(f"Completed in {elapsed:.2f} seconds\n")

        # Generate results
        failures = [r for r in self.results if not r.passed]
        total_passed = sum(s.passed for s in self.category_stats.values())
        total_failed = sum(s.failed for s in self.category_stats.values())

        metadata = {
            "language": self.language,
            "total_tests": self.num_tests,
            "passed": total_passed,
            "failed": total_failed,
            "pass_rate": round(total_passed / self.num_tests * 100, 2),
            "elapsed_seconds": round(elapsed, 2),
            "seed": self.seed,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        results = BenchmarkResults(
            metadata=metadata,
            category_stats=self.category_stats,
            failures=failures[:100],  # Limit to first 100 failures
            failure_analysis=self.analyzer.generate_analysis(),
        )

        return results

    def print_results(self, results: BenchmarkResults) -> None:
        """Print formatted results to console."""
        print(f"\n{'=' * 70}")
        print("RESULTS")
        print(f"{'=' * 70}\n")

        # Overall stats
        meta = results.metadata
        print(f"Total Tests: {meta['total_tests']}")
        print(f"Passed: {meta['passed']} ({meta['pass_rate']}%)")
        print(f"Failed: {meta['failed']} ({100 - meta['pass_rate']:.2f}%)")
        print(f"Time: {meta['elapsed_seconds']}s")
        print()

        # Category results
        print("Category Results:")
        for category, stats in sorted(results.category_stats.items()):
            status = "✓" if stats.pass_rate >= 95 else "✗"
            pct = stats.pass_rate
            print(f"  {status} {category}: {stats.passed}/{stats.total} ({pct:.1f}%)")
        print()

        # Failure analysis
        if results.failures:
            print("Failure Analysis:")
            analysis = results.failure_analysis

            if analysis["by_failure_type"]:
                print("\n  By Failure Type:")
                for ftype, count in sorted(
                    analysis["by_failure_type"].items(), key=lambda x: -x[1]
                ):
                    print(f"    {ftype}: {count}")

            if analysis["by_apostrophe_type"]:
                print("\n  By Apostrophe Type:")
                for atype, count in sorted(
                    analysis["by_apostrophe_type"].items(), key=lambda x: -x[1]
                ):
                    print(f"    {atype}: {count}")

            if analysis["by_quote_type"]:
                print("\n  By Quote Type:")
                for qtype, count in sorted(
                    analysis["by_quote_type"].items(), key=lambda x: -x[1]
                ):
                    print(f"    {qtype}: {count}")

            if analysis["by_punctuation"]:
                print("\n  By Punctuation:")
                for punct, count in sorted(
                    analysis["by_punctuation"].items(), key=lambda x: -x[1]
                )[:10]:
                    print(f"    {repr(punct)}: {count}")

            print("\n  Sample Failures (first 10):")
            for failure in results.failures[:10]:
                print(f"\n    Test #{failure.test_id} ({failure.category}):")
                print(f"      Text: {failure.text}")
                print(f"      Expected: {failure.expected_phonemes}")
                print(f"      Actual:   {failure.actual_phonemes}")
                print(f"      Type: {failure.failure_type}")
                if failure.params:
                    print(f"      Params: {failure.params}")

        print(f"\n{'=' * 70}\n")


# =============================================================================
# Main
# =============================================================================


def main():
    """Run benchmark with command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Benchmark English G2P quotes, contractions, and punctuation handling"
        )
    )
    parser.add_argument(
        "--language",
        default="en-us",
        choices=["en-us", "en-gb"],
        help="Language variant to test",
    )
    parser.add_argument(
        "--num-tests", type=int, default=1000, help="Number of random tests to generate"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    parser.add_argument(
        "--verbose", action="store_true", help="Print detailed progress"
    )

    args = parser.parse_args()

    # Run benchmark
    benchmark = QuotesContractionsBenchmark(
        language=args.language,
        num_tests=args.num_tests,
        seed=args.seed,
        verbose=args.verbose,
    )

    results = benchmark.run()
    benchmark.print_results(results)

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
