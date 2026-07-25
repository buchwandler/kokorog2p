#!/usr/bin/env python3
"""
Quick demo of disabling Dr. and replacing it with Drive.

This is exactly what you asked for:
- Disable the existing "Dr." abbreviation
- Add a new "Dr." that expands to "Drive"
"""

from kokorog2p import get_g2p

# Get the G2P instance
g2p = get_g2p("en-us")

print("Original behavior:")
print("-" * 50)
text1 = "Dr. Smith lives on Elm Dr."
print(f"Input:  {text1}")
print(f"Output: {g2p.phonemize(text1)}")
print()

# Step 1: Remove the existing Dr. abbreviation
print("Customizing abbreviations:")
print("-" * 50)
print("1. Removing 'Dr.' abbreviation...")
g2p.remove_abbreviation("Dr.")
print(f"   'Dr.' exists: {g2p.has_abbreviation('Dr.')}")
print()

# Step 2: Add new Dr. → Drive
print("2. Adding 'Dr.' → 'Drive'...")
g2p.add_abbreviation("Dr.", "Drive", description="Drive (street type)")
print(f"   'Dr.' exists: {g2p.has_abbreviation('Dr.')}")
print()

# Step 3: Test the result
print("New behavior:")
print("-" * 50)
test_cases = [
    "I live on Main Dr.",
    "Turn left on Oak Dr.",
    "Dr. Smith lives at 123 Elm Dr.",
]

for text in test_cases:
    result = g2p.phonemize(text)
    print(f"Input:  {text}")
    print(f"Output: {result}")
    print()

print("=" * 50)
print("✓ Done! Dr. now always expands to 'Drive'")
