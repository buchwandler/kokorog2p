#!/usr/bin/env python3
"""
Example: Customizing Abbreviations in kokorog2p

This example demonstrates how to:
1. Remove existing abbreviations
2. Add custom abbreviations
3. Replace abbreviations with different expansions
4. Use context-aware abbreviations

Author: kokorog2p
"""

from kokorog2p import get_g2p


def example_1_remove_abbreviation():
    """Example 1: Remove an abbreviation so it won't be expanded."""
    print("=" * 70)
    print("Example 1: Removing an abbreviation")
    print("=" * 70)

    g2p = get_g2p("en-us")

    # Before removal
    text = "Dr. Smith lives on Main Street."
    result_before = g2p.phonemize(text)
    print(f"Before: {text}")
    print(f"  → {result_before}")

    # Remove the Dr. abbreviation
    g2p.remove_abbreviation("Dr.")

    # After removal (Dr. won't be expanded to "Doctor")
    result_after = g2p.phonemize(text)
    print("\nAfter removing 'Dr.':")
    print(f"  → {result_after}")
    print()


def example_2_replace_abbreviation():
    """Example 2: Replace Dr. to always expand to 'Drive'."""
    print("=" * 70)
    print("Example 2: Replacing Dr. with Drive")
    print("=" * 70)

    g2p = get_g2p("en-us")

    # Remove the original Dr. abbreviation
    g2p.remove_abbreviation("Dr.")

    # Add new abbreviation that always expands to "Drive"
    g2p.add_abbreviation("Dr.", "Drive", description="Drive (street type)")

    # Test it
    text1 = "I live on Main Dr."
    text2 = "Visit Dr. Smith."

    print(f"Text 1: {text1}")
    print(f"  → {g2p.phonemize(text1)}")
    print(f"\nText 2: {text2}")
    print(f"  → {g2p.phonemize(text2)}")
    print("\nNote: Now 'Dr.' always expands to 'Drive', even before names!")
    print()


def example_3_add_custom_abbreviation():
    """Example 3: Add a new custom abbreviation."""
    print("=" * 70)
    print("Example 3: Adding a custom abbreviation")
    print("=" * 70)

    g2p = get_g2p("en-us")

    # Add a custom abbreviation
    g2p.add_abbreviation("Tech.", "Technology", description="Technology")

    text = "Tech. is advancing rapidly in modern society."
    result = g2p.phonemize(text)

    print(f"Text: {text}")
    print(f"  → {result}")
    print("\n'Tech.' expands to 'Technology'")

    # Clean up
    g2p.remove_abbreviation("Tech.")
    print()


def example_4_context_aware_abbreviation():
    """Example 4: Context-aware abbreviation with different expansions."""
    print("=" * 70)
    print("Example 4: Context-aware abbreviation")
    print("=" * 70)

    g2p = get_g2p("en-us")

    # Add a context-aware abbreviation
    # "Av." could mean "Avenue" in addresses or "Average" in other contexts
    g2p.add_abbreviation(
        "Av.",
        {"default": "Average", "place": "Avenue"},
        description="Avenue or Average (context-dependent)",
    )

    text1 = "The av. temperature is 72°F."
    text2 = "I live on Park Av."

    print(f"Text 1 (default context): {text1}")
    print(f"  → {g2p.phonemize(text1)}")

    print(f"\nText 2 (place context): {text2}")
    print(f"  → {g2p.phonemize(text2)}")

    # Clean up
    g2p.remove_abbreviation("Av.")
    print()


def example_5_list_abbreviations():
    """Example 5: List all available abbreviations."""
    print("=" * 70)
    print("Example 5: Listing abbreviations")
    print("=" * 70)

    g2p = get_g2p("en-us")

    abbrevs = g2p.list_abbreviations()

    print(f"Total abbreviations: {len(abbrevs)}")
    print("\nSample abbreviations:")

    # Show first 20
    for abbrev in sorted(abbrevs)[:20]:
        print(f"  - {abbrev}")

    print(f"\n... and {len(abbrevs) - 20} more")

    # Check if specific abbreviation exists
    print("\nChecking specific abbreviations:")
    print(f"  'Dr.' exists: {g2p.has_abbreviation('Dr.')}")
    print(f"  'Prof.' exists: {g2p.has_abbreviation('Prof.')}")
    print(f"  'Xyz.' exists: {g2p.has_abbreviation('Xyz.')}")
    print()


def example_6_your_use_case():
    """Example 6: Your specific use case - disable Dr. and replace with Drive."""
    print("=" * 70)
    print("Example 6: Your use case - Dr. → Drive")
    print("=" * 70)

    from kokorog2p import clear_cache

    # Clear cache to start fresh
    clear_cache()

    g2p = get_g2p("en-us")

    # Step 1: Remove existing Dr. abbreviation
    print("Step 1: Remove 'Dr.' abbreviation")
    g2p.remove_abbreviation("Dr.")
    print(f"  'Dr.' exists: {g2p.has_abbreviation('Dr.')}")

    # Step 2: Add new Dr. abbreviation that expands to "Drive"
    print("\nStep 2: Add 'Dr.' → 'Drive'")
    g2p.add_abbreviation("Dr.", "Drive", description="Drive (street type)")
    print(f"  'Dr.' exists: {g2p.has_abbreviation('Dr.')}")

    # Step 3: Test it
    print("\nStep 3: Test the changes")
    test_texts = [
        "I live on Main Dr.",
        "Turn left on Oak Dr.",
        "123 Elm Dr. is my address.",
    ]

    for text in test_texts:
        result = g2p.phonemize(text)
        print(f"  {text}")
        print(f"    → {result}")

    print()


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "ABBREVIATION CUSTOMIZATION EXAMPLES" + " " * 18 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    example_1_remove_abbreviation()
    example_2_replace_abbreviation()
    example_3_add_custom_abbreviation()
    example_4_context_aware_abbreviation()
    example_5_list_abbreviations()
    example_6_your_use_case()

    print("=" * 70)
    print("All examples completed!")
    print("=" * 70)


if __name__ == "__main__":
    main()
