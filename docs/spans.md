# Span-Based Phonemization Guide

This document explains the span-based (offset-based) phonemization system in kokorog2p,
which provides deterministic, pipeline-friendly text-to-phoneme conversion.

## Overview

The span-based system uses **character offsets** to precisely identify and override
specific portions of text during phonemization. This approach is more robust than
word-based matching because it handles:

- **Duplicate words** with different pronunciations (e.g., "the cat the dog")
- **Partial word matches** (e.g., distinguishing "cat" from "category")
- **Complex text structures** with punctuation and whitespace variations
- **Pipeline integration** with offset-preserving preprocessing

## Core Types

### `TokenSpan`

Represents a single token with its phonemization and metadata:

```python
@dataclass
class TokenSpan:
    text: str              # Original text ("hello")
    start: int             # Character offset start (0)
    end: int               # Character offset end (5)
    phonemes: str = ""     # Phonemized text ("həlˈO")
    lang: str | None = None  # Language override ("en-us", "fr", etc.)
    custom_attrs: dict[str, str] = field(default_factory=dict)
```

**Key Properties:**

- `start` and `end` are **character offsets** in the clean text (after markup removal)
- `end` is **exclusive** (Python slice convention: `text[start:end]`)
- Multiple tokens can reference the same text position if tokenization creates sub-parts

**Example:**

```python
text = "Hello world!"
tokens = tokenize_with_offsets(text)
# TokenSpan(text="Hello", start=0, end=5, ...)
# TokenSpan(text=" ", start=5, end=6, ...)
# TokenSpan(text="world", start=6, end=11, ...)
# TokenSpan(text="!", start=11, end=12, ...)
```

### `OverrideSpan`

Specifies a region of text to override during phonemization:

```python
@dataclass
class OverrideSpan:
    start: int                      # Character offset start
    end: int                        # Character offset end (exclusive)
    attrs: dict[str, str]           # Override attributes
```

**Common Attributes:**

- `ph`: Direct phoneme override (e.g., `{"ph": "həlˈO"}`)
- `lang`: Language switch (e.g., `{"lang": "fr"}`)
- Custom attributes for pipeline processing

**Example:**

```python
text = "the cat the dog"
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),   # First "the" → /ðə/
    OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the" → /ði/
]
```

### `PhonemizeResult`

The complete phonemization output:

```python
@dataclass
class PhonemizeResult:
    phonemes: str                   # Concatenated phoneme string
    token_ids: list[int] | None     # Optional token IDs for model input
    tokens: list[TokenSpan]         # Detailed token-level information
    warnings: list[str]             # Alignment warnings
```

## Character Offset Coordinate System

### Basic Rules

1. **Zero-indexed**: First character is at position `0`
2. **Exclusive end**: Range `[start, end)` means characters from `start` up to but not
   including `end`
3. **Clean text reference**: Offsets refer to text **after** markup removal but
   **before** normalization

### Examples

```python
text = "Hello world"
#       0123456789...

# "Hello" → start=0, end=5
# "world" → start=6, end=11
# " " (space) → start=5, end=6
```

### With Markup

```python
# Original: "[Hello]{ph='həlˈO'} world"
# Clean text: "Hello world"
#              0123456789...

override = OverrideSpan(0, 5, {"ph": "həlˈO"})  # Refers to "Hello" in clean text
```

### Duplicate Words

```python
text = "the cat the dog"
#       012345678901234...

# First "the" → OverrideSpan(0, 3, ...)
# Second "the" → OverrideSpan(8, 11, ...)
```

## Alignment Modes

The system supports two alignment modes for applying overrides to tokens:

### 1. Span Alignment (Default, `alignment="span"`)

**Recommended for all new code.** Uses character offsets for deterministic matching.

**Matching Logic:**

- **Exact match**: Override span exactly matches token span → Apply override
- **Partial overlap** (snap mode): Override partially overlaps token → Apply with
  warning
- **No overlap**: Override doesn't touch token → Skip

**Advantages:**

- ✅ Handles duplicate words correctly
- ✅ No ambiguity in complex text
- ✅ Predictable behavior for pipeline integration
- ✅ Works with partial word matches

**Example:**

```python
result = phonemize_to_result(
    "the cat the dog",
    overrides=[
        OverrideSpan(0, 3, {"ph": "ðə"}),
        OverrideSpan(8, 11, {"ph": "ði"}),
    ],
    alignment="span"  # default
)
# Both overrides applied to correct "the" instances
```

### 2. Legacy Word Alignment (`alignment="legacy"`)

**Deprecated.** Uses word-text matching (first occurrence).

**Matching Logic:**

- Finds first token with matching text
- Cannot distinguish between duplicate words
- Provided only for backward compatibility

**Limitations:**

- ❌ Cannot handle duplicate words with different overrides
- ❌ Order-dependent behavior
- ❌ Fragile with whitespace/punctuation variations

**Example:**

```python
result = phonemize_to_result(
    "the cat the dog",
    overrides=[
        OverrideSpan(0, 3, {"ph": "ðə"}),
        OverrideSpan(8, 11, {"ph": "ði"}),  # Will NOT work correctly!
    ],
    alignment="legacy"
)
# Only first "the" gets overridden (both overrides apply to same word)
```

## Overlap Handling

When an override partially overlaps with a token, the system can handle it in two ways:

### Snap Mode (Default, `overlap="snap"`)

Apply the override and emit a warning:

```python
result = phonemize_to_result(
    "category",
    overrides=[OverrideSpan(0, 3, {"ph": "kæt"})],  # "cat" is only part of "category"
    overlap="snap"
)
# Override applied to entire "category" token
# Warning: "Override 0:3 partially overlaps token 'category' (0:8)"
```

### Strict Mode (`overlap="strict"`)

Raise an error on partial overlap:

```python
result = phonemize_to_result(
    "category",
    overrides=[OverrideSpan(0, 3, {"ph": "kæt"})],
    overlap="strict"
)
# Raises ValueError: "Override 0:3 partially overlaps token 'category' (0:8)"
```

## Language Switching

Override spans can specify language changes for specific text regions:

```python
# Mix English and French in same sentence
text = "Hello Bonjour world"
overrides = [
    OverrideSpan(6, 13, {"lang": "fr"})  # "Bonjour" in French
]

result = phonemize_to_result(text, overrides=overrides, lang="en-us")
# "Hello" → English G2P
# "Bonjour" → French G2P
# "world" → English G2P
```

**Language Codes:**

- Use standard language codes: `en-us`, `fr`, `de`, `es`, etc.
- See `get_g2p()` for supported languages

## Phoneme Overrides

Direct phoneme replacement bypasses G2P processing:

```python
text = "read the book"
overrides = [
    OverrideSpan(0, 4, {"ph": "ɹˈEd"}),  # "read" as past tense
]

result = phonemize_to_result(text, overrides=overrides)
# Uses provided phonemes for "read" instead of G2P lookup
```

**Phoneme Override Priority:** If both `ph` and `lang` are specified, `ph` takes
precedence:

```python
OverrideSpan(0, 5, {"ph": "test", "lang": "fr"})
# "ph" is used, "lang" is ignored for this span
```

## Custom Attributes

Override spans can carry custom attributes for downstream processing:

```python
overrides = [
    OverrideSpan(0, 5, {
        "ph": "həlˈO",
        "speaker": "male",
        "emphasis": "strong"
    })
]

result = phonemize_to_result(text, overrides=overrides)
# Custom attributes stored in token.custom_attrs
for token in result.tokens:
    print(token.custom_attrs)  # {"speaker": "male", "emphasis": "strong"}
```

## Best Practices

### 1. Use Span Alignment (Default)

Always use span-based alignment unless you have a specific reason to use legacy mode:

```python
# ✅ Good
result = phonemize_to_result(text, overrides=overrides)

# ❌ Avoid (unless backward compatibility required)
result = phonemize_to_result(text, overrides=overrides, alignment="legacy")
```

### 2. Compute Offsets from Clean Text

Always compute offsets from the text **after** markup removal:

```python
# Original markup text
markup_text = "[Hello]{ph='test'} world"

# Remove markup to get clean text
clean_text = "Hello world"

# Compute offsets from clean text
override = OverrideSpan(0, 5, {"ph": "həlˈO"})  # Refers to "Hello" in clean_text
```

### 3. Use `tokenize_with_offsets()` for Debugging

Inspect tokenization to understand offset positions:

```python
from kokorog2p import tokenize_with_offsets

text = "the cat the dog"
tokens = tokenize_with_offsets(text)

for tok in tokens:
    print(f"{tok.text!r} → [{tok.start}:{tok.end}]")
# 'the' → [0:3]
# ' ' → [3:4]
# 'cat' → [4:7]
# ...
```

### 4. Check Warnings

Always inspect `result.warnings` to catch alignment issues:

```python
result = phonemize_to_result(text, overrides=overrides)

if result.warnings:
    print("Alignment warnings:")
    for warning in result.warnings:
        print(f"  - {warning}")
```

### 5. Test with Duplicates

Always test your override logic with duplicate words:

```python
# ✅ Good test case
text = "the cat saw the dog"
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),    # First "the"
    OverrideSpan(12, 15, {"ph": "ði"}),  # Second "the"
]
result = phonemize_to_result(text, overrides=overrides)
assert len(result.warnings) == 0
```

## Common Pitfalls

### ❌ Using Word Offsets Instead of Character Offsets

```python
# WRONG: These are word positions, not character offsets
override = OverrideSpan(0, 1, {"ph": "test"})  # Trying to select first word

# RIGHT: Use character positions
text = "hello world"
override = OverrideSpan(0, 5, {"ph": "test"})  # "hello" is chars 0-5
```

### ❌ Ignoring Clean Text vs Original Text

```python
# Original: "[Hello]{lang='fr'} world"
# Clean: "Hello world"

# WRONG: Offsets based on original text
override = OverrideSpan(0, 7, {"ph": "test"})  # Includes markup chars

# RIGHT: Offsets based on clean text
override = OverrideSpan(0, 5, {"ph": "test"})  # Just "Hello"
```

### ❌ Forgetting Exclusive End

```python
text = "hello"
#       01234

# WRONG: Inclusive end
override = OverrideSpan(0, 4, {"ph": "test"})  # Only covers "hell"

# RIGHT: Exclusive end
override = OverrideSpan(0, 5, {"ph": "test"})  # Covers "hello"
```

### ❌ Assuming Legacy Alignment Works with Duplicates

```python
# WRONG: Legacy alignment cannot handle this correctly
text = "the cat the dog"
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),
    OverrideSpan(8, 11, {"ph": "ði"}),
]
result = phonemize_to_result(text, overrides=overrides, alignment="legacy")
# Both overrides apply to first "the" only!

# RIGHT: Use span alignment (default)
result = phonemize_to_result(text, overrides=overrides)
# Correctly applies to each "the" instance
```

## See Also

- [API Documentation](api.md) - Main API functions
- [SSMD Documentation](ssmd.md) - Markup syntax for creating override spans
- [Examples](../examples/new_api_demo.py) - Working code examples
