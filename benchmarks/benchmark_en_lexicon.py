#!/usr/bin/env python3
"""Benchmark English lexicon entries against fallback outputs.

Compares lexicon phonemes (gold or silver) to fallback phonemes (espeak or goruut)
using EnglishG2P with lexicon loading disabled.

Run with: python -m benchmarks.benchmark_en_lexicon
"""

import random
import time
from dataclasses import dataclass

from kokorog2p.en.g2p import EnglishG2P
from kokorog2p.en.lexicon import Lexicon

PRIMARY_STRESS = "\u02c8"
SECONDARY_STRESS = "\u02cc"


@dataclass
class BenchmarkResult:
    language: str
    lexicon: str
    fallback: str
    total_words: int
    matched: int
    mismatched: int
    errors: int
    total_time_ms: float
    words_per_second: float

    def __str__(self) -> str:
        return (
            f"\n{'=' * 60}\n"
            f"Benchmark: English Lexicon vs {self.fallback}\n"
            f"{'=' * 60}\n"
            f"Language:         {self.language}\n"
            f"Lexicon tier:     {self.lexicon}\n"
            f"Fallback:         {self.fallback}\n"
            f"Total words:      {self.total_words:,}\n"
            f"Matched:          {self.matched:,}\n"
            f"Mismatched:       {self.mismatched:,}\n"
            f"Errors:           {self.errors:,}\n"
            f"Accuracy:         {self._accuracy():.2f}%\n"
            f"Total time:       {self.total_time_ms:.2f} ms\n"
            f"Words/second:     {self.words_per_second:,.0f}\n"
        )

    def _accuracy(self) -> float:
        if self.total_words == 0:
            return 0.0
        return (self.matched / self.total_words) * 100


def normalize_phonemes(phonemes: str | None, strip_stress: bool) -> str:
    if not phonemes:
        return ""
    if strip_stress:
        return phonemes.replace(PRIMARY_STRESS, "").replace(SECONDARY_STRESS, "")
    return phonemes


def get_lexicon_entry(entry: str | dict[str, str | None]) -> str | None:
    if isinstance(entry, dict):
        default = entry.get("DEFAULT")
        if default:
            return default
        for value in entry.values():
            if value:
                return value
        return None
    return entry


def get_fallback_phonemes(g2p: EnglishG2P, word: str) -> str | None:
    tokens = g2p(word)
    for token in tokens:
        if token.text and any(c.isalnum() for c in token.text):
            return token.phonemes
    if tokens:
        return tokens[0].phonemes
    return None


def benchmark_lexicon(
    language: str = "en-us",
    lexicon: str = "gold",
    fallback: str = "espeak",
    strip_stress: bool = False,
    limit: int | None = None,
) -> tuple[
    BenchmarkResult, list[tuple[str, str, str]], dict[str, int], dict[str, tuple]
]:
    british = language == "en-gb"
    use_gold = lexicon == "gold"
    use_silver = lexicon == "silver"

    lex = Lexicon(british=british, load_gold=use_gold, load_silver=use_silver)
    entries = lex.golds if use_gold else lex.silvers

    words = sorted(entries.keys())
    if limit is not None:
        words = words[:limit]

    g2p = EnglishG2P(
        language=language,
        use_espeak_fallback=fallback == "espeak",
        use_goruut_fallback=fallback == "goruut",
        use_spacy=False,
        expand_abbreviations=False,
        enable_context_detection=False,
        load_silver=False,
        load_gold=False,
        strict=False,
    )

    matched = 0
    mismatched = 0
    errors = 0
    sample_differences: list[tuple[str, str, str]] = []
    diff_count = 0
    substitutions: dict[str, int] = {}
    substitutions_words: dict[str, tuple] = {}

    start_time = time.perf_counter()

    for word in words:
        entry = entries[word]
        lex_ps = get_lexicon_entry(entry)
        if lex_ps is None:
            errors += 1
            diff_count += 1
            entry = (word, "None", "None")
            if len(sample_differences) < 10:
                sample_differences.append(entry)
            else:
                idx = random.randrange(diff_count)
                if idx < 10:
                    sample_differences[idx] = entry
            continue

        try:
            fallback_ps = get_fallback_phonemes(g2p, word)
        except Exception as exc:
            errors += 1
            diff_count += 1
            entry = (word, lex_ps, f"Error: {exc}")
            if len(sample_differences) < 10:
                sample_differences.append(entry)
            else:
                idx = random.randrange(diff_count)
                if idx < 10:
                    sample_differences[idx] = entry
            continue

        lex_norm = normalize_phonemes(lex_ps, strip_stress)
        fallback_norm = normalize_phonemes(fallback_ps, strip_stress)

        lex_nostress = normalize_phonemes(lex_ps, True)
        fallback_nostress = normalize_phonemes(fallback_ps, True)

        if len(lex_nostress) == len(fallback_nostress):
            for lex_char, fallback_char in zip(
                lex_nostress, fallback_nostress, strict=False
            ):
                if lex_char != fallback_char:
                    key = f"{lex_char}_{fallback_char}"
                    substitutions[key] = substitutions.get(key, 0) + 1
                    substitutions_words[key] = (word, lex_nostress, fallback_nostress)

        if lex_norm == fallback_norm:
            matched += 1
        else:
            mismatched += 1
            diff_count += 1
            entry = (word, lex_ps, fallback_ps or "None")
            if len(sample_differences) < 10:
                sample_differences.append(entry)
            else:
                idx = random.randrange(diff_count)
                if idx < 10:
                    sample_differences[idx] = entry

    end_time = time.perf_counter()
    total_time_ms = (end_time - start_time) * 1000
    total_words = len(words)

    result = BenchmarkResult(
        language=language,
        lexicon=lexicon,
        fallback=fallback,
        total_words=total_words,
        matched=matched,
        mismatched=mismatched,
        errors=errors,
        total_time_ms=total_time_ms,
        words_per_second=total_words / (total_time_ms / 1000)
        if total_time_ms > 0
        else 0,
    )

    return result, sample_differences, substitutions, substitutions_words


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Benchmark English lexicon against fallback outputs"
    )
    parser.add_argument(
        "--language",
        choices=["en-us", "en-gb"],
        default="en-us",
        help="Language variant (default: en-us)",
    )
    parser.add_argument(
        "--lexicon",
        choices=["gold", "silver"],
        default="gold",
        help="Lexicon tier to benchmark (default: gold)",
    )
    parser.add_argument(
        "--fallback",
        choices=["espeak", "goruut"],
        default="espeak",
        help="Fallback engine to compare (default: espeak)",
    )
    parser.add_argument(
        "--strip-stress",
        action="store_true",
        help="Strip stress markers before comparison",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of words processed",
    )

    args = parser.parse_args()

    result, differences, substitutions, substitutions_words = benchmark_lexicon(
        language=args.language,
        lexicon=args.lexicon,
        fallback=args.fallback,
        strip_stress=args.strip_stress,
        limit=args.limit,
    )

    print(result)

    if differences:
        print("10 random differences (word | lexicon | fallback):")
        for word, lex_ps, fallback_ps in differences:
            print(f"  {word} | {lex_ps} | {fallback_ps}")

    if substitutions:
        print("\nSubstitution counts (stress stripped, same-length only):")
        for key, count in sorted(
            substitutions.items(), key=lambda item: item[1], reverse=True
        ):
            lex_char, fallback_char = key.split("_", 1)
            print(
                f"  {lex_char} -> {fallback_char} | {count} | "
                f"{substitutions_words[key][0]}: {substitutions_words[key][1]} "
                f"-> {substitutions_words[key][2]}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
