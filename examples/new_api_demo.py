"""
Example demonstrating the new span-based phonemization API.

This script shows how to use the pipeline-friendly API for deterministic
phonemization with overrides.
"""

from kokorog2p import OverrideSpan, phonemize

# Example 1: Simple phonemization with the new API
print("=" * 70)
print("Example 1: Simple phonemization")
print("=" * 70)

result = phonemize("Hello world!")
print(f"Text: {result.clean_text}")
print(f"Phonemes: {result.phonemes}")
print(f"Token IDs: {result.token_ids[:10]}...")  # First 10 IDs
print(f"Tokens: {len(result.tokens)}")
print(f"Warnings: {result.warnings}")
print()

# Example 2: Phonemization with phoneme override
print("=" * 70)
print("Example 2: With phoneme override")
print("=" * 70)

text = "Hello world!"
# Override "Hello" to use custom phonemes
overrides = [OverrideSpan(0, 5, {"ph": "hɛˈloʊ"})]
result = phonemize(text, overrides=overrides)

print(f"Text: {result.clean_text}")
print(f"Phonemes: {result.phonemes}")
print(f"Override applied: {'hɛˈloʊ' in result.phonemes}")
print()

# Example 3: Handling duplicate words with different phonemes
print("=" * 70)
print("Example 3: Duplicate words with different phonemes")
print("=" * 70)

text = "the cat the dog"
# Apply different pronunciations to each "the"
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),  # First "the" (unstressed)
    OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the" (stressed)
]
result = phonemize(text, overrides=overrides)

print(f"Text: {result.clean_text}")
print(f"Phonemes: {result.phonemes}")
print(f"Both overrides applied: {'ðə' in result.phonemes and 'ði' in result.phonemes}")
print()

# Example 4: Language switching within text
print("=" * 70)
print("Example 4: Per-span language switching")
print("=" * 70)

text = "Hello Bonjour Welt"
# "Bonjour" in French, "Welt" in German
overrides = [
    OverrideSpan(6, 13, {"lang": "fr"}),
    OverrideSpan(14, 18, {"lang": "de"}),
]
result = phonemize(text, language="en-us", overrides=overrides)

print(f"Text: {result.clean_text}")
print(f"Phonemes: {result.phonemes}")
print(f"Token 1 lang: {result.tokens[1].lang}")  # Bonjour - French
print(f"Token 2 lang: {result.tokens[2].lang}")  # Welt - German
print()

# Example 5: Mixed attributes (phoneme + language)
print("=" * 70)
print("Example 5: Mixed attributes")
print("=" * 70)

text = "Say Bonjour nicely"
# Override both phonemes AND language
overrides = [OverrideSpan(4, 11, {"ph": "bɔ̃ʒuʁ", "lang": "fr"})]
result = phonemize(text, language="en-us", overrides=overrides)

print(f"Text: {result.clean_text}")
print(f"Phonemes: {result.phonemes}")
print(f"'Bonjour' token lang: {result.tokens[1].lang}")
print(f"'Bonjour' phonemes: {result.tokens[1].meta.get('phonemes')}")
print()

# Example 6: Warnings and debugging
print("=" * 70)
print("Example 6: Warnings for misaligned overrides")
print("=" * 70)

text = "Hello world"
# Override that partially overlaps tokens (will snap and warn)
overrides = [OverrideSpan(2, 8, {"ph": "test"})]
result = phonemize(text, overrides=overrides)

print(f"Text: {result.clean_text}")
print(f"Warnings: {result.warnings}")
print(f"Override snapped to tokens: {result.tokens[0].meta.get('ph')}")
print()

# Example 8: Reusing G2P instance for performance
print("=" * 70)
print("Example 8: Reusing G2P for performance")
print("=" * 70)

texts = ["Hello!", "World!", "Test!"]
for text in texts:
    result = phonemize(text)
    print(f"{text} -> {result.phonemes}")

print("\n" + "=" * 70)
print("All examples completed!")
print("=" * 70)
