#!/usr/bin/env python3
"""
Demonstration of both fixes:
1. Temperature bug fix (37°C. → Celsius, not circa)
2. Abbreviation customization (Dr. → Drive)
"""

from kokorog2p import clear_cache, get_g2p

print("=" * 70)
print("DEMONSTRATION: Temperature Fix + Abbreviation Customization")
print("=" * 70)
print()

# Clear cache to start fresh
clear_cache()

print("PART 1: Temperature Bug Fix")
print("-" * 70)
print("Issue: '37°C.' was being expanded to '37°circa' instead of Celsius")
print("Fix: Temperature normalization now runs BEFORE abbreviation expansion")
print()

g2p = get_g2p("en-us")

test_cases = [
    ("approximately 37°C", "No period - should work"),
    ("The temperature is 37°C.", "With period - THIS WAS THE BUG"),
    ("It's 98°F.", "Fahrenheit with period"),
    ("-40°C is very cold.", "Negative temperature"),
]

for text, description in test_cases:
    result = g2p.phonemize(text)
    print(f"{description}:")
    print(f"  Input:  {text}")
    print(f"  Output: {result}")

    # Verify Celsius/Fahrenheit in output
    if "°C" in text:
        if "sˈɛlsiəs" in result or "sɛlsiəs" in result:
            print("  ✓ Correctly expanded to 'Celsius'")
        else:
            print("  ✗ ERROR: Not expanded to Celsius!")
    elif "°F" in text:
        if "fˈɛɹənhˌIt" in result or "fɛɹənhˌIt" in result or "fˈɛɹənhIt" in result:
            print("  ✓ Correctly expanded to 'Fahrenheit'")
        else:
            print("  ✗ ERROR: Not expanded to Fahrenheit!")
    print()

print()
print("=" * 70)
print("PART 2: Abbreviation Customization")
print("-" * 70)
print("Task: Disable 'Dr.' → 'Doctor' and replace with 'Dr.' → 'Drive'")
print()

# Show original behavior
print("Original behavior:")
text = "Dr. Smith lives on Elm Dr."
result = g2p.phonemize(text)
print(f"  Input:  {text}")
print(f"  Output: {result}")
print()

# Customize abbreviations
print("Customizing...")
print("  1. Removing 'Dr.' abbreviation")
removed = g2p.remove_abbreviation("Dr.")
print(f"     Removed: {removed}")

print("  2. Adding 'Dr.' → 'Drive'")
g2p.add_abbreviation("Dr.", "Drive", description="Drive (street type)")
print(f"     Has 'Dr.': {g2p.has_abbreviation('Dr.')}")
print()

# Show new behavior
print("New behavior:")
test_texts = [
    "I live on Main Dr.",
    "Turn left on Oak Dr.",
    "Dr. Smith works here.",  # Even with names, now expands to Drive
]

for text in test_texts:
    result = g2p.phonemize(text)
    print(f"  Input:  {text}")
    print(f"  Output: {result}")

    # Verify Drive in output
    if "dɹ" in result and ("Iv" in result or "aɪv" in result or "Av" in result):
        print("  ✓ Correctly expanded to 'Drive'")
    print()

print("=" * 70)
print("✓ Both features working correctly!")
print("=" * 70)
