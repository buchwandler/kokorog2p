# Pipeline API Reference

This document provides comprehensive API documentation for kokorog2p's pipeline-friendly
phonemization functions.

## Table of Contents

- [Main Functions](#main-functions)
  - [phonemize_to_result](#phonemize_to_result)
  - [phonemize_ssmd](#phonemize_ssmd)
  - [phonemize_ssmd_to_result](#phonemize_ssmd_to_result)
- [Utility Functions](#utility-functions)
  - [tokenize_with_offsets](#tokenize_with_offsets)
  - [gtokens_to_tokenspans](#gtokens_to_tokenspans)
- [Types](#types)
- [Examples](#examples)

---

## Main Functions

### `phonemize_to_result`

Convert text to phonemes with optional span-based overrides.

```python
def phonemize_to_result(
    text: str,
    *,
    lang: str = "en-us",
    overrides: list[OverrideSpan] | None = None,
    return_phonemes: bool = True,
    return_ids: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    overlap: Literal["snap", "strict"] = "snap",
    g2p_instance: G2PBase | None = None,
) -> PhonemizeResult:
```

**Parameters:**

- **`text`** (`str`): Input text to phonemize (clean text without markup)
- **`lang`** (`str`, default: `"en-us"`): Default language code for phonemization
- **`overrides`** (`list[OverrideSpan] | None`, default: `None`): List of span overrides
  for custom phonemes or language switching
- **`return_phonemes`** (`bool`, default: `True`): Include concatenated phoneme string
  in result
- **`return_ids`** (`bool`, default: `True`): Include token IDs in result
- **`alignment`** (`Literal["span", "legacy"]`, default: `"span"`):
  - `"span"`: Use offset-based alignment (recommended, handles duplicates)
  - `"legacy"`: Use word-based alignment (deprecated, for backward compatibility)
- **`overlap`** (`Literal["snap", "strict"]`, default: `"snap"`):
  - `"snap"`: Apply partial overlaps with warning
  - `"strict"`: Raise error on partial overlaps
- **`g2p_instance`** (`G2PBase | None`, default: `None`): Reuse existing G2P instance
  for performance

**Returns:** `PhonemizeResult`

**Raises:**

- `ValueError`: If `overlap="strict"` and partial overlap detected
- `ValueError`: If unsupported language specified

**Example:**

```python
from kokorog2p import phonemize_to_result, OverrideSpan

# Simple phonemization
result = phonemize_to_result("Hello world!")
print(result.phonemes)  # 'hɛˈloʊ wˈɜɹld!'

# With overrides
text = "the cat the dog"
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),   # First "the"
    OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the"
]
result = phonemize_to_result(text, overrides=overrides)

# Language switching
text = "Hello Bonjour world"
overrides = [OverrideSpan(6, 13, {"lang": "fr"})]
result = phonemize_to_result(text, lang="en-us", overrides=overrides)

# Performance: reuse G2P instance
from kokorog2p import get_g2p

g2p = get_g2p("en-us")
result1 = phonemize_to_result(text1, g2p_instance=g2p)
result2 = phonemize_to_result(text2, g2p_instance=g2p)
```

---

### `phonemize_ssmd`

Phonemize SSMD-formatted text (convenience wrapper).

```python
def phonemize_ssmd(
    ssmd_text: str,
    *,
    lang: str = "en-us",
    return_phonemes: bool = True,
    return_ids: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    overlap: Literal["snap", "strict"] = "snap",
    g2p_instance: G2PBase | None = None,
) -> str | list[int] | tuple[str, list[int]]:
```

**Parameters:**

Same as `phonemize_to_result` except:

- **`ssmd_text`** (`str`): Input text with SSMD markup (e.g., `"[Hello]{ph='test'}"`)

**Returns:**

- `str`: Phoneme string (if `return_phonemes=True, return_ids=False`)
- `list[int]`: Token IDs (if `return_phonemes=False, return_ids=True`)
- `tuple[str, list[int]]`: Both (if both `True`)

**Example:**

```python
from kokorog2p import phonemize_ssmd

# Simple SSMD
phonemes = phonemize_ssmd("[Hello]{ph='həlˈO'} world")
print(phonemes)  # 'həlˈO wˈɜɹld'

# Get both phonemes and IDs
phonemes, ids = phonemize_ssmd(
    "[the]{ph='ðə'} cat",
    return_phonemes=True,
    return_ids=True
)
```

---

### `phonemize_ssmd_to_result`

Phonemize SSMD text and return detailed result.

```python
def phonemize_ssmd_to_result(
    ssmd_text: str,
    *,
    lang: str = "en-us",
    return_phonemes: bool = True,
    return_ids: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    overlap: Literal["snap", "strict"] = "snap",
    g2p_instance: G2PBase | None = None,
) -> PhonemizeResult:
```

**Parameters:**

Same as `phonemize_ssmd`.

**Returns:** `PhonemizeResult` (with full token-level details)

**Example:**

```python
from kokorog2p import phonemize_ssmd_to_result

result = phonemize_ssmd_to_result("[the]{ph='ðə'} cat [the]{ph='ði'} dog")

print(result.phonemes)  # 'ðə kˈæt ði dˈɔɡ'
print(len(result.tokens))  # 7 (including spaces/words)

# Check warnings
if result.warnings:
    print("Warnings:", result.warnings)

# Inspect tokens
for tok in result.tokens:
    print(f"{tok.text!r}: {tok.phonemes}")
```

---

## Utility Functions

### `tokenize_with_offsets`

Tokenize text and compute character offsets for each token.

```python
def tokenize_with_offsets(
    text: str,
    include_punctuation: bool = True
) -> list[TokenSpan]:
```

**Parameters:**

- **`text`** (`str`): Input text to tokenize
- **`include_punctuation`** (`bool`, default: `True`): Include punctuation and
  whitespace as tokens

**Returns:** `list[TokenSpan]` (without phonemes, just text and offsets)

**Example:**

```python
from kokorog2p import tokenize_with_offsets

text = "Hello, world!"
tokens = tokenize_with_offsets(text)

for tok in tokens:
    print(f"{tok.text!r} → [{tok.start}:{tok.end}]")

# Output:
# 'Hello' → [0:5]
# ',' → [5:6]
# ' ' → [6:7]
# 'world' → [7:12]
# '!' → [12:13]
```

**Use Cases:**

- Debugging offset calculations
- Understanding tokenization behavior
- Creating OverrideSpan instances programmatically

---

### `gtokens_to_tokenspans`

Convert G2P token objects to `TokenSpan` objects.

```python
def gtokens_to_tokenspans(
    gtokens: list[Any],
    start_offset: int = 0
) -> list[TokenSpan]:
```

**Parameters:**

- **`gtokens`** (`list[Any]`): List of G2P token objects (from `g2p.tokenize()`)
- **`start_offset`** (`int`, default: `0`): Starting character offset

**Returns:** `list[TokenSpan]`

**Example:**

```python
from kokorog2p import get_g2p, gtokens_to_tokenspans

g2p = get_g2p("en-us")
gtokens = g2p.tokenize("Hello world")
token_spans = gtokens_to_tokenspans(gtokens)

for ts in token_spans:
    print(f"{ts.text} @ [{ts.start}:{ts.end}]")
```

**Note:** This is primarily an internal utility function. Most users should use
`tokenize_with_offsets()` instead.

---

## Types

### `TokenSpan`

Represents a single token with phonemes and metadata.

```python
@dataclass
class TokenSpan:
    text: str                           # Original token text
    start: int                          # Character offset start (inclusive)
    end: int                            # Character offset end (exclusive)
    phonemes: str = ""                  # Phonemized output
    lang: str | None = None             # Language override
    custom_attrs: dict[str, str] = field(default_factory=dict)
```

**Fields:**

- **`text`**: Original text of the token (e.g., `"hello"`)
- **`start`**: Starting character position in clean text (0-indexed)
- **`end`**: Ending character position (exclusive, Python slice convention)
- **`phonemes`**: Phonemized version of the text (empty before phonemization)
- **`lang`**: Language code if different from default (e.g., `"fr"`)
- **`custom_attrs`**: Custom attributes from override spans (e.g.,
  `{"speaker": "male"}`)

---

### `OverrideSpan`

Specifies a region to override during phonemization.

```python
@dataclass
class OverrideSpan:
    start: int                          # Character offset start (inclusive)
    end: int                            # Character offset end (exclusive)
    attrs: dict[str, str]               # Override attributes
```

**Fields:**

- **`start`**: Starting character position in clean text
- **`end`**: Ending character position (exclusive)
- **`attrs`**: Attribute dictionary:
  - `"ph"`: Direct phoneme override (e.g., `{"ph": "həlˈO"}`)
  - `"lang"`: Language switch (e.g., `{"lang": "fr"}`)
  - Custom keys: Any other attributes for downstream processing

**Precedence:**

- If both `"ph"` and `"lang"` are present, `"ph"` takes precedence
- Custom attributes are preserved in `TokenSpan.custom_attrs`

---

### `PhonemizeResult`

Complete phonemization output with metadata.

```python
@dataclass
class PhonemizeResult:
    phonemes: str                       # Concatenated phoneme string
    token_ids: list[int] | None         # Token IDs (if return_ids=True)
    tokens: list[TokenSpan]             # Token-level details
    warnings: list[str]                 # Alignment warnings
```

**Fields:**

- **`phonemes`**: Full phoneme string with all tokens concatenated
- **`token_ids`**: List of integer token IDs for model input (or `None` if
  `return_ids=False`)
- **`tokens`**: Detailed list of all tokens with individual phonemes and metadata
- **`warnings`**: List of warning messages (e.g., partial overlaps, missing matches)

**Note:** Always check `warnings` to catch potential alignment issues.

---

## Examples

### Example 1: Basic Phonemization

```python
from kokorog2p import phonemize_to_result

result = phonemize_to_result("Hello world!")

print("Phonemes:", result.phonemes)
print("Token IDs:", result.token_ids)
print("Warnings:", result.warnings)
```

### Example 2: Duplicate Word Overrides

```python
from kokorog2p import phonemize_to_result, OverrideSpan

text = "the cat the dog"
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),   # First "the" → /ðə/
    OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the" → /ði/
]

result = phonemize_to_result(text, overrides=overrides)

# Both "the" instances get different pronunciations
for tok in result.tokens:
    if tok.text == "the":
        print(f"'the' @ [{tok.start}:{tok.end}] → {tok.phonemes}")
```

### Example 3: Language Switching

```python
from kokorog2p import phonemize_to_result, OverrideSpan

text = "I speak English and français"
overrides = [
    OverrideSpan(20, 28, {"lang": "fr"})  # "français" in French
]

result = phonemize_to_result(text, lang="en-us", overrides=overrides)

for tok in result.tokens:
    if tok.lang:
        print(f"{tok.text} → language: {tok.lang}, phonemes: {tok.phonemes}")
```

### Example 4: SSMD Markup

```python
from kokorog2p import phonemize_ssmd_to_result

ssmd = "[the]{ph='ðə'} cat [the]{ph='ði'} dog"
result = phonemize_ssmd_to_result(ssmd)

print("Phonemes:", result.phonemes)
print("Tokens:", len(result.tokens))

# Check each token
for tok in result.tokens:
    print(f"  {tok.text!r} → {tok.phonemes!r}")
```

### Example 5: Custom Attributes

```python
from kokorog2p import phonemize_to_result, OverrideSpan

text = "Hello world"
overrides = [
    OverrideSpan(0, 5, {
        "ph": "həlˈO",
        "speaker": "alice",
        "emphasis": "strong"
    })
]

result = phonemize_to_result(text, overrides=overrides)

for tok in result.tokens:
    if tok.custom_attrs:
        print(f"{tok.text}: {tok.custom_attrs}")
```

### Example 6: Performance (Reusing G2P Instance)

```python
from kokorog2p import phonemize_to_result, get_g2p

# Create G2P instance once
g2p = get_g2p("en-us")

# Reuse for multiple phonemizations
texts = ["Hello", "Goodbye", "Thank you"]
results = [
    phonemize_to_result(text, g2p_instance=g2p)
    for text in texts
]

for text, result in zip(texts, results):
    print(f"{text} → {result.phonemes}")
```

### Example 7: Token ID Output Only

```python
from kokorog2p import phonemize_to_result

# Get only token IDs (skip phoneme string generation)
result = phonemize_to_result(
    "Hello world",
    return_phonemes=False,
    return_ids=True
)

print(result.phonemes)  # Empty string ""
print(result.token_ids)  # [50, 83, 54, ...]
```

### Example 8: Debugging with Tokenization

```python
from kokorog2p import tokenize_with_offsets, phonemize_to_result, OverrideSpan

text = "the cat the dog"

# First, inspect tokenization
tokens = tokenize_with_offsets(text)
print("Tokens:")
for tok in tokens:
    print(f"  {tok.text!r} → [{tok.start}:{tok.end}]")

# Create precise overrides based on offsets
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),    # First "the"
    OverrideSpan(8, 11, {"ph": "ði"}),   # Second "the"
]

result = phonemize_to_result(text, overrides=overrides)
print("\nResult:", result.phonemes)
print("Warnings:", result.warnings)
```

### Example 9: Strict Overlap Checking

```python
from kokorog2p import phonemize_to_result, OverrideSpan

text = "category"

# This override only covers "cat" (0:3) but token is "category" (0:8)
override = OverrideSpan(0, 3, {"ph": "kæt"})

try:
    result = phonemize_to_result(
        text,
        overrides=[override],
        overlap="strict"  # Raise error on partial overlap
    )
except ValueError as e:
    print(f"Error: {e}")

# Use snap mode instead (default)
result = phonemize_to_result(
    text,
    overrides=[override],
    overlap="snap"  # Apply with warning
)
print("Warnings:", result.warnings)
```

---

## Migration from Legacy API

### Old API (String-Based)

```python
from kokorog2p import phonemize

# Old way
phonemes = phonemize("Hello world")
```

### New API (Span-Based)

```python
from kokorog2p import phonemize_to_result

# New way (backward compatible)
result = phonemize_to_result("Hello world")
phonemes = result.phonemes

# Or use convenience wrapper for drop-in replacement
from kokorog2p import phonemize_ssmd
phonemes = phonemize_ssmd("Hello world")
```

### Old SSMD API

```python
from kokorog2p.speechmarkdown import speechmarkdown_to_phonemes

# Old way
phonemes = speechmarkdown_to_phonemes("[the]{ph='ðə'} cat")
```

### New SSMD API

```python
from kokorog2p import phonemize_ssmd, phonemize_ssmd_to_result

# Simple replacement
phonemes = phonemize_ssmd("[the]{ph='ðə'} cat")

# With detailed results
result = phonemize_ssmd_to_result("[the]{ph='ðə'} cat")
phonemes = result.phonemes
token_ids = result.token_ids
```

---

## See Also

- [Span Documentation](spans.md) - Understanding character offsets and alignment
- [SSMD Documentation](ssmd.md) - Markup syntax for annotations
- [Examples](../examples/new_api_demo.py) - Complete working examples
