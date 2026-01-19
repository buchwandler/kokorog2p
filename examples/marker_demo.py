#!/usr/bin/env python3
"""Demo: Marker-based override system for kokorog2p.

This example demonstrates how to use the marker-delimited helper
to easily mark text spans and apply pronunciation or language overrides.
"""

from kokorog2p import phonemize_to_result
from kokorog2p.markers import apply_marker_overrides, parse_delimited


def demo_basic_markers():
    """Basic example: Simple phoneme overrides."""
    print("=" * 70)
    print("Demo 1: Basic Phoneme Overrides")
    print("=" * 70)

    # Mark words with @ delimiter
    text = "I really like @pecan@ pie and @coffee@."
    print(f"\nInput text: {text}")

    # Step 1: Parse markers to get clean text and ranges
    clean_text, ranges, warnings = parse_delimited(text, marker="@")
    print(f"Clean text: {clean_text}")
    print(f"Marked ranges: {ranges}")

    # Step 2: Assign phoneme overrides
    assignments = {
        1: {"ph": "pɪˈkɑːn"},  # First marker: "pecan"
        2: {"ph": "ˈkɔfi"},  # Second marker: "coffee"
    }

    # Step 3: Convert to overrides and phonemize
    overrides = apply_marker_overrides(clean_text, ranges, assignments)
    result = phonemize_to_result(clean_text, lang="en-us", overrides=overrides)

    print(f"\nPhonemes: {result.phonemes}")
    print(f"Warnings: {result.warnings if result.warnings else 'None'}")


def demo_duplicate_words():
    """Handle duplicate words with different pronunciations."""
    print("\n" + "=" * 70)
    print("Demo 2: Duplicate Words (Different Pronunciations)")
    print("=" * 70)

    # The word "the" appears twice with different pronunciations
    text = "@the@ cat @the@ dog"
    print(f"\nInput text: {text}")

    clean_text, ranges, _ = parse_delimited(text, marker="@")
    print(f"Clean text: {clean_text}")

    # Different phonemes for each "the"
    assignments = {
        1: {"ph": "ðə"},  # Reduced form
        2: {"ph": "ði"},  # Emphasized form
    }

    overrides = apply_marker_overrides(clean_text, ranges, assignments)
    result = phonemize_to_result(clean_text, lang="en-us", overrides=overrides)

    print(f"Phonemes: {result.phonemes}")


def demo_language_switching():
    """Switch languages within a sentence."""
    print("\n" + "=" * 70)
    print("Demo 3: Language Switching")
    print("=" * 70)

    # Mix German and English
    text = "Das ist @Machine Learning@ für bessere @Performance@."
    print(f"\nInput text: {text}")

    clean_text, ranges, _ = parse_delimited(text, marker="@")

    # Mark English words
    assignments = {
        1: {"lang": "en-us"},  # "Machine Learning"
        2: {"lang": "en-us"},  # "Performance"
    }

    overrides = apply_marker_overrides(clean_text, ranges, assignments)
    result = phonemize_to_result(clean_text, lang="de", overrides=overrides)

    print(f"Phonemes: {result.phonemes}")


def demo_multi_word_spans():
    """Mark multi-word expressions."""
    print("\n" + "=" * 70)
    print("Demo 4: Multi-Word Spans")
    print("=" * 70)

    text = "I visited @New York City@ last summer."
    print(f"\nInput text: {text}")

    clean_text, ranges, _ = parse_delimited(text, marker="@")

    # Override pronunciation for the entire city name
    assignments = {
        1: {"ph": "nuː jɔːk ˈsɪti"},
    }

    overrides = apply_marker_overrides(clean_text, ranges, assignments)
    result = phonemize_to_result(clean_text, lang="en-us", overrides=overrides)

    print(f"Phonemes: {result.phonemes}")


def demo_custom_markers():
    """Use different marker characters."""
    print("\n" + "=" * 70)
    print("Demo 5: Custom Marker Characters")
    print("=" * 70)

    # Use # instead of @
    text = "The price is #100# dollars."
    print(f"\nInput text: {text}")

    clean_text, ranges, _ = parse_delimited(text, marker="#")

    assignments = {
        1: {"ph": "wʌn ˈhʌndrəd"},
    }

    overrides = apply_marker_overrides(clean_text, ranges, assignments)
    result = phonemize_to_result(clean_text, lang="en-us", overrides=overrides)

    print(f"Phonemes: {result.phonemes}")


def demo_escaped_markers():
    """Handle escaped markers (literal @ in text)."""
    print("\n" + "=" * 70)
    print("Demo 6: Escaped Markers")
    print("=" * 70)

    # Use \@ to include literal @ in text
    text = "Email me at user\\@example.com or visit @website@."
    print(f"\nInput text: {text}")

    clean_text, ranges, warnings = parse_delimited(text, marker="@", escape="\\")
    print(f"Clean text: {clean_text}")
    print(f"Marked ranges: {ranges}")  # Only "website" is marked

    assignments = {
        1: {"ph": "ˈwɛbsaɪt"},
    }

    overrides = apply_marker_overrides(clean_text, ranges, assignments)
    result = phonemize_to_result(clean_text, lang="en-us", overrides=overrides)

    print(f"Phonemes: {result.phonemes}")


def demo_list_assignments():
    """Use list-based assignments instead of dict."""
    print("\n" + "=" * 70)
    print("Demo 7: List-Based Assignments (Sequential)")
    print("=" * 70)

    text = "I like @coffee@, @tea@, and @water@."
    print(f"\nInput text: {text}")

    clean_text, ranges, _ = parse_delimited(text, marker="@")

    # Use list for sequential assignment (must match range count)
    assignments = [
        {"ph": "ˈkɔfi"},
        {"ph": "tiː"},
        {},  # Empty dict = no override for "water"
    ]

    overrides = apply_marker_overrides(clean_text, ranges, assignments)
    result = phonemize_to_result(clean_text, lang="en-us", overrides=overrides)

    print(f"Phonemes: {result.phonemes}")


def demo_error_handling():
    """Show warning handling for unmatched markers."""
    print("\n" + "=" * 70)
    print("Demo 8: Warning Handling (Unmatched Markers)")
    print("=" * 70)

    # Intentionally create unmatched marker
    text = "This has @unmatched marker in it."
    print(f"\nInput text: {text}")

    clean_text, ranges, warnings = parse_delimited(text, marker="@")
    print(f"Clean text: {clean_text}")
    print(f"Marked ranges: {ranges}")
    print(f"Warnings: {warnings}")

    # Text still works, just no marked ranges
    result = phonemize_to_result(clean_text, lang="en-us")
    print(f"Phonemes: {result.phonemes}")


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("KOKOROG2P MARKER SYSTEM DEMO")
    print("=" * 70)

    demo_basic_markers()
    demo_duplicate_words()
    demo_language_switching()
    demo_multi_word_spans()
    demo_custom_markers()
    demo_escaped_markers()
    demo_list_assignments()
    demo_error_handling()

    print("\n" + "=" * 70)
    print("END OF DEMOS")
    print("=" * 70)


if __name__ == "__main__":
    main()
