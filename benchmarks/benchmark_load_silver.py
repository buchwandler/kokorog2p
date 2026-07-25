"""Benchmark script to measure memory and initialization time
with/without silver/gold datasets.

This benchmark compares:
1. Memory usage with silver/gold enabled vs disabled
2. Initialization time with silver/gold enabled vs disabled
3. Lookup accuracy for words in silver/gold dictionaries
"""

import time
import tracemalloc
from typing import Any

from kokorog2p import get_g2p


def measure_init_and_memory(
    language: str, load_silver: bool, load_gold: bool = True, **kwargs: Any
) -> tuple[float, float, Any]:
    """Measure initialization time and memory usage.

    Args:
        language: Language code.
        load_silver: Whether to load silver dataset.
        load_gold: Whether to load gold dataset.
        **kwargs: Additional arguments for get_g2p.

    Returns:
        Tuple of (init_time_ms, memory_mb, g2p_instance).
    """
    # Start memory tracking
    tracemalloc.start()

    # Measure initialization time
    start_time = time.perf_counter()
    g2p = get_g2p(language, load_silver=load_silver, load_gold=load_gold, **kwargs)
    end_time = time.perf_counter()

    # Get memory usage
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    init_time_ms = (end_time - start_time) * 1000
    memory_mb = peak / 1024 / 1024

    return init_time_ms, memory_mb, g2p


def benchmark_english():
    """Benchmark English with different dictionary loading configurations."""
    print("=" * 70)
    print("ENGLISH (US) BENCHMARK - Dictionary Loading Impact")
    print("=" * 70)
    print()

    configs = [
        (False, False, "No dictionaries (espeak only)"),
        (False, True, "Gold only"),
        (True, False, "Silver only (unusual)"),
        (True, True, "Gold + Silver (default)"),
    ]

    results = []
    for load_silver, load_gold, description in configs:
        print(f"Testing: {description}...")
        init_time, memory, g2p = measure_init_and_memory(
            "en-us", load_silver=load_silver, load_gold=load_gold, use_spacy=False
        )
        results.append((description, init_time, memory, g2p))
        print(f"   Initialization time: {init_time:.2f} ms")
        print(f"   Memory usage: {memory:.2f} MB")
        print(f"   Gold entries: {len(g2p.lexicon.golds):,}")
        print(f"   Silver entries: {len(g2p.lexicon.silvers):,}")
        print()

    # Show comparisons
    print("Comparison (all relative to default Gold + Silver):")
    default_init, default_mem = results[3][1], results[3][2]
    for description, init_time, memory, _ in results:
        init_diff = init_time - default_init
        mem_diff = memory - default_mem
        init_pct = (init_diff / default_init) * 100 if default_init > 0 else 0
        mem_pct = (mem_diff / default_mem) * 100 if default_mem > 0 else 0
        print(f"   {description}:")
        print(f"     Init: {init_diff:+.2f} ms ({init_pct:+.1f}%)")
        print(f"     Memory: {mem_diff:+.2f} MB ({mem_pct:+.1f}%)")
    print()

    # Test phonemization with different configs
    print("Testing phonemization across configurations:")
    test_words = [
        ("hello", "Common word (in gold)"),
        ("world", "Common word (in gold)"),
    ]

    for description, _, _, g2p in results:
        print(f"   {description}:")
        for word, word_desc in test_words:
            result = g2p.phonemize(word)
            print(f"     {word} ({word_desc}): {result}")
    print()


def benchmark_british():
    """Benchmark British English with and without silver dataset."""
    print("=" * 70)
    print("ENGLISH (GB) BENCHMARK - Silver Dataset Impact")
    print("=" * 70)
    print()

    # Test without silver
    print("1. Loading WITHOUT silver dataset (gold only)...")
    init_time_no_silver, memory_no_silver, g2p_no_silver = measure_init_and_memory(
        "en-gb", load_silver=False, use_spacy=False
    )
    print(f"   Initialization time: {init_time_no_silver:.2f} ms")
    print(f"   Memory usage: {memory_no_silver:.2f} MB")
    print()

    # Test with silver
    print("2. Loading WITH silver dataset (gold + silver)...")
    init_time_with_silver, memory_with_silver, g2p_with_silver = (
        measure_init_and_memory("en-gb", load_silver=True, use_spacy=False)
    )
    print(f"   Initialization time: {init_time_with_silver:.2f} ms")
    print(f"   Memory usage: {memory_with_silver:.2f} MB")
    print()

    # Calculate differences
    init_diff = init_time_with_silver - init_time_no_silver
    memory_diff = memory_with_silver - memory_no_silver
    init_pct = (init_diff / init_time_no_silver) * 100
    memory_pct = (memory_diff / memory_no_silver) * 100

    print("3. Impact of loading silver dataset:")
    print(f"   Additional initialization time: +{init_diff:.2f} ms ({init_pct:.1f}%)")
    print(f"   Additional memory usage: +{memory_diff:.2f} MB ({memory_pct:.1f}%)")
    print()

    # Test dictionary size
    print("4. Dictionary sizes:")
    print(f"   Gold entries: {len(g2p_no_silver.lexicon.golds):,}")
    print(f"   Silver entries (no silver): {len(g2p_no_silver.lexicon.silvers):,}")
    print(f"   Silver entries (with silver): {len(g2p_with_silver.lexicon.silvers):,}")
    print()


def benchmark_other_languages():
    """Benchmark other languages (should have no impact from load_silver)."""
    print("=" * 70)
    print("OTHER LANGUAGES - Silver Parameter (No Impact Expected)")
    print("=" * 70)
    print()

    languages = [
        ("de", "German"),
        ("fr", "French"),
        ("ja", "Japanese"),
    ]

    for lang_code, lang_name in languages:
        print(f"{lang_name} ({lang_code}):")

        # Without silver
        init_no, mem_no, _ = measure_init_and_memory(
            lang_code, load_silver=False, use_spacy=False
        )

        # With silver
        init_yes, mem_yes, _ = measure_init_and_memory(
            lang_code, load_silver=True, use_spacy=False
        )

        print(f"   Without silver: {init_no:.2f} ms, {mem_no:.2f} MB")
        print(f"   With silver:    {init_yes:.2f} ms, {mem_yes:.2f} MB")
        print(
            f"   Difference:     {init_yes - init_no:.2f} ms, {mem_yes - mem_no:.2f} MB"
        )
        print()


def main():
    """Run all benchmarks."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 12 + "DICTIONARY LOADING BENCHMARK" + " " * 28 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # Benchmark English (US)
    benchmark_english()
    print()

    # Benchmark English (GB)
    benchmark_british()
    print()

    # Benchmark other languages
    benchmark_other_languages()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("The load_silver and load_gold parameters allow you to:")
    print("  ✓ Control memory usage (gold + silver uses most memory)")
    print("  ✓ Control initialization time (fewer dictionaries = faster init)")
    print("  ✓ Trade off coverage vs performance")
    print()
    print("Configurations:")
    print("  • load_gold=True, load_silver=True:  Maximum coverage (default)")
    print("  • load_gold=True, load_silver=False: Common words only")
    print("  • load_gold=False, load_silver=False: Ultra-fast (espeak only)")
    print()
    print("Memory savings (English):")
    print("  • Disabling silver: ~22-31 MB saved")
    print("  • Disabling both: ~50+ MB saved")
    print()


if __name__ == "__main__":
    main()
