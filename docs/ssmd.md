# SSMD (Speech Synthesis Markup for Documentation) Syntax

This document describes the SSMD annotation syntax supported by kokorog2p for specifying
pronunciation overrides and language switches within text.

## Overview

SSMD uses a lightweight markup syntax inspired by Markdown:

```
[text to annotate]{attribute="value"}
```

This allows you to embed pronunciation hints directly in your text without requiring
separate offset calculations.

## Basic Syntax

### Simple Annotation

```
[word]{attribute="value"}
```

**Example:**

```python
from kokorog2p import phonemize_ssmd

result = phonemize_ssmd("[hello]{ph='həlˈO'}")
# Output: "həlˈO"
```

### Multiple Words

```
[multiple words]{attribute="value"}
```

**Example:**

```python
result = phonemize_ssmd("[New York]{ph='nuː jɔːɹk'}")
# Output: "nuː jɔːɹk"
```

### Multiple Annotations

```
[word1]{attr="val1"} and [word2]{attr="val2"}
```

**Example:**

```python
result = phonemize_ssmd("[the]{ph='ðə'} cat and [the]{ph='ði'} dog")
# Output: "ðə kˈæt ænd ði dˈɔɡ"
```

---

## Attributes

### Phoneme Override (`ph`)

Directly specify the phonemes for a word or phrase.

**Syntax:**

```
[word]{ph="phonemes"}
```

**Examples:**

```python
# Override pronunciation
phonemize_ssmd("[read]{ph='ɹˈEd'} the book")  # Past tense "read"
phonemize_ssmd("[read]{ph='ɹˈiːd'} the book")  # Present tense "read"

# Handle proper nouns
phonemize_ssmd("Meet [Sean]{ph='ʃɔːn'}")  # Not "siːn"

# Fix homographs
phonemize_ssmd("I [live]{ph='lˈɪv'} in [Live]{ph='lˈaɪv'} Oak")
```

**IPA Characters:** The `ph` attribute accepts any valid IPA characters. Common symbols:

- Vowels: `a`, `e`, `i`, `o`, `u`, `æ`, `ɛ`, `ɪ`, `ɔ`, `ʊ`, etc.
- Consonants: `p`, `t`, `k`, `b`, `d`, `g`, `m`, `n`, `ŋ`, `f`, `v`, etc.
- Stress: `ˈ` (primary), `ˌ` (secondary)
- Length: `ː` (long vowel)

### Language Switch (`lang`)

Switch to a different language for specific words/phrases.

**Syntax:**

```
[word]{lang="language-code"}
```

**Supported Languages:**

- `en-us`: English (US)
- `en-gb`: English (UK)
- `fr`: French
- `de`: German
- `es`: Spanish
- `it`: Italian
- `ko`: Korean
- `cs`: Czech
- `he`: Hebrew
- And more (see `get_g2p()` documentation)

**Examples:**

```python
# French word in English sentence
phonemize_ssmd("I love [Paris]{lang='fr'}", lang="en-us")

# German name with proper pronunciation
phonemize_ssmd("Meet [München]{lang='de'} tomorrow", lang="en-us")

# Multi-language sentence
phonemize_ssmd(
    "Say [hello]{lang='en-us'} [bonjour]{lang='fr'} [hola]{lang='es'}",
    lang="en-us"
)
```

### Custom Attributes

Any additional attributes are preserved in `TokenSpan.custom_attrs`:

**Syntax:**

```
[word]{attr1="value1" attr2="value2"}
```

**Examples:**

```python
from kokorog2p import phonemize_ssmd_to_result

result = phonemize_ssmd_to_result(
    "[Hello]{speaker='alice' emphasis='strong'} [world]{speaker='bob'}"
)

for tok in result.tokens:
    if tok.custom_attrs:
        print(f"{tok.text}: {tok.custom_attrs}")

# Output:
# Hello: {'speaker': 'alice', 'emphasis': 'strong'}
# world: {'speaker': 'bob'}
```

---

## Quote Styles

SSMD supports multiple quote styles for attribute values:

### Double Quotes (Recommended)

```
[word]{attr="value"}
```

**Example:**

```python
phonemize_ssmd('[hello]{ph="həlˈO"}')
```

### Single Quotes

```
[word]{attr='value'}
```

**Example:**

```python
phonemize_ssmd("[hello]{ph='həlˈO'}")
```

### Mixed Quotes

Different attributes can use different quote styles:

```
[word]{attr1="value1" attr2='value2'}
```

**Example:**

```python
phonemize_ssmd('[hello]{ph="həlˈO" lang=\'en-us\'}')
```

### Nested Quotes

Use different quote styles for nesting:

```
[word]{attr="value with 'quotes'"}
[word]{attr='value with "quotes"'}
```

**Example:**

```python
phonemize_ssmd('[test]{note="It\'s working"}')
phonemize_ssmd("[test]{note='She said \"hello\"'}")
```

### Escape Sequences

Escape quotes within same-style quotes:

```
[word]{attr="value with \"escaped\" quotes"}
[word]{attr='value with \'escaped\' quotes'}
```

**Example:**

```python
phonemize_ssmd('[test]{ph="test \\"value\\""}')
phonemize_ssmd("[test]{ph='test \\'value\\''}]")
```

---

## Advanced Features

### Special Characters in Keys

Attribute keys can contain hyphens and colons:

**Hyphens:**

```
[word]{voice-name="alice"}
[word]{data-speaker="bob"}
```

**Colons (XML-style):**

```
[word]{xml:lang="en-us"}
[word]{aria:label="greeting"}
```

**Example:**

```python
result = phonemize_ssmd_to_result(
    "[Hello]{ph='həlˈO' voice-name='alice' xml:lang='en-us'}"
)

tok = result.tokens[0]
print(tok.custom_attrs)
# {'voice-name': 'alice', 'xml:lang': 'en-us'}
```

### Empty Attribute Values

Attributes can have empty values:

```
[word]{flag=""}
```

**Example:**

```python
result = phonemize_ssmd_to_result('[word]{processed=""}')
# custom_attrs = {'processed': ''}
```

### Whitespace in Attributes

Whitespace around `=` is optional:

```
[word]{attr="value"}
[word]{attr = "value"}
[word]{ attr = "value" }
```

All are equivalent.

### Unicode in Values

Full Unicode support in attribute values:

```
[word]{ph="日本語"}
[word]{note="Emoji 🎉 supported"}
```

**Example:**

```python
phonemize_ssmd('[test]{ph="bɔ̃ʒuʁ"}')  # French nasalized vowel
```

---

## Duplicate Word Handling

SSMD with span-based alignment (default) handles duplicate words correctly:

```python
from kokorog2p import phonemize_ssmd

# Each annotation applies to the correct instance
result = phonemize_ssmd("[the]{ph='ðə'} cat [the]{ph='ði'} dog")
# Output: "ðə kˈæt ði dˈɔɡ"
```

Under the hood:

1. SSMD parser extracts clean text: `"the cat the dog"`
2. Parser computes offsets for each annotation:
   - First `[the]` → `OverrideSpan(0, 3, {"ph": "ðə"})`
   - Second `[the]` → `OverrideSpan(8, 11, {"ph": "ði"})`
3. Span-based alignment matches each override to the correct word

**Legacy Mode Warning:** If you use `alignment="legacy"`, duplicate annotations will
fail:

```python
# DON'T DO THIS
result = phonemize_ssmd(
    "[the]{ph='ðə'} cat [the]{ph='ði'} dog",
    alignment="legacy"  # Both overrides apply to first "the"!
)
```

---

## Grammar Reference

### Formal Syntax

```
annotation := '[' text ']' '{' attributes '}'

attributes := attribute | attribute whitespace attributes

attribute := key '=' quoted_value

key := [a-zA-Z]+ [a-zA-Z0-9_:-]*

quoted_value := '"' ( [^"] | '\"' )* '"'
              | "'" ( [^'] | "\'" )* "'"

text := any characters (no brackets)
```

### SSMD Parsing Pipeline

1. **Extract annotations**: Find all `[text]{attrs}` patterns
2. **Parse attributes**: Extract key-value pairs from `{...}`
3. **Compute clean text**: Remove markup to get plain text
4. **Calculate offsets**: Map annotations to character positions in clean text
5. **Create spans**: Build `OverrideSpan` objects with offsets and attributes
6. **Phonemize**: Apply spans to phonemization process

---

## Examples

### Example 1: Simple Override

```python
from kokorog2p import phonemize_ssmd

phonemes = phonemize_ssmd("[hello]{ph='həlˈO'}")
print(phonemes)  # "həlˈO"
```

### Example 2: Multiple Annotations

```python
phonemes = phonemize_ssmd(
    "[the]{ph='ðə'} [cat]{ph='kæt'} sat on [the]{ph='ði'} mat"
)
print(phonemes)  # "ðə kæt sˈæt ɑn ði mˈæt"
```

### Example 3: Language Switching

```python
phonemes = phonemize_ssmd(
    "Welcome to [Paris]{lang='fr'}, the city of lights",
    lang="en-us"
)
```

### Example 4: Mixed Attributes

```python
from kokorog2p import phonemize_ssmd_to_result

result = phonemize_ssmd_to_result(
    "[hello]{ph='həlˈO' speaker='alice'} [world]{lang='fr' speaker='bob'}"
)

for tok in result.tokens:
    print(f"{tok.text}: phonemes={tok.phonemes}, attrs={tok.custom_attrs}")
```

### Example 5: Proper Nouns

```python
phonemes = phonemize_ssmd(
    "I met [Siobhan]{ph='ʃɪˈvɔːn'} at [Leicester]{ph='lˈɛstə'} Square",
    lang="en-gb"
)
```

### Example 6: Complex Sentence

```python
from kokorog2p import phonemize_ssmd

ssmd = """
The [colonel]{ph='kˈɜɹnəl'} said [read]{ph='ɹˈEd'} the [record]{ph='ɹˈɛkɜɹd'}.
I will [record]{ph='ɹɪkˈɔɹd'} you as you [read]{ph='ɹˈiːd'} it aloud.
"""

phonemes = phonemize_ssmd(ssmd)
print(phonemes)
```

### Example 7: Multilingual

```python
phonemes = phonemize_ssmd(
    "Greetings: [Hello]{lang='en-us'}, [Bonjour]{lang='fr'}, [Hola]{lang='es'}, [Ciao]{lang='it'}",
    lang="en-us"
)
```

### Example 8: Custom Annotations for TTS

```python
from kokorog2p import phonemize_ssmd_to_result

result = phonemize_ssmd_to_result(
    "[Hello]{speaker='alice' pitch='high'} said Alice. "
    "[Hello]{speaker='bob' pitch='low'} replied Bob."
)

# Extract speaker-specific phonemes
for tok in result.tokens:
    if "speaker" in tok.custom_attrs:
        print(f"{tok.custom_attrs['speaker']}: {tok.phonemes}")
```

---

## SSMD vs. Manual Spans

### When to Use SSMD

✅ **Use SSMD when:**

- Writing text with inline annotations
- Working with human-readable text
- You need a simple syntax for annotating pronunciation
- You're creating test cases or examples

### When to Use Manual Spans

✅ **Use `OverrideSpan` directly when:**

- Programmatically generating overrides
- Integrating with external annotation tools
- You already have character offsets from preprocessing
- Building a pipeline that preserves offsets

**Example Comparison:**

```python
from kokorog2p import phonemize_ssmd, phonemize_to_result, OverrideSpan

# SSMD (human-friendly)
result1 = phonemize_ssmd("[the]{ph='ðə'} cat")

# Manual spans (pipeline-friendly)
result2 = phonemize_to_result(
    "the cat",
    overrides=[OverrideSpan(0, 3, {"ph": "ðə"})]
)

# Both produce identical results
assert result1 == result2.phonemes
```

---

## Limitations

### Current Limitations

1. **No nested annotations**: Cannot nest `[...]` within `[...]`

   ```python
   # NOT SUPPORTED:
   # "[outer [inner]{...}]{...}"
   ```

2. **No attribute inheritance**: Each annotation is independent

   ```python
   # Must specify lang for each word:
   phonemize_ssmd("[Bonjour]{lang='fr'} [Paris]{lang='fr'}")
   # No way to set default lang for a region
   ```

3. **No escaping brackets in text**: Use phoneme override for text with brackets
   ```python
   # If you need literal brackets, use ph override:
   phonemize_ssmd("[test]{ph='tɛst [bracketed]'}")
   ```

### Error Handling

**Malformed attributes** are silently ignored:

```python
# Missing quotes - ignored
phonemize_ssmd("[word]{attr=value}")

# Missing equals - ignored
phonemize_ssmd("[word]{attr}")

# Unclosed quote - ignored
phonemize_ssmd('[word]{attr="value}')
```

Check `result.warnings` to catch issues:

```python
from kokorog2p import phonemize_ssmd_to_result

result = phonemize_ssmd_to_result("[test]{malformed}")
if result.warnings:
    print("Warnings:", result.warnings)
```

---

## Best Practices

### 1. Use Consistent Quote Style

Pick one quote style and stick to it:

```python
# ✅ Good - consistent
phonemize_ssmd('[word1]{ph="a"} [word2]{ph="b"}')

# ❌ Avoid - inconsistent (but valid)
phonemize_ssmd('[word1]{ph="a"} [word2]{ph=\'b\'}')
```

### 2. Validate Phonemes

Ensure phonemes use valid IPA:

```python
# ✅ Good - valid IPA
phonemize_ssmd("[hello]{ph='həlˈoʊ'}")

# ❌ Bad - non-IPA characters
phonemize_ssmd("[hello]{ph='heh-LOW'}")  # Will work but inconsistent
```

### 3. Test with Duplicates

Always test annotations with duplicate words:

```python
# ✅ Good - handles duplicates
ssmd = "[the]{ph='ðə'} cat and [the]{ph='ði'} dog"
result = phonemize_ssmd(ssmd)

# Verify both overrides applied
assert "ðə" in result
assert "ði" in result
```

### 4. Use Language Codes Correctly

Verify language codes are supported:

```python
from kokorog2p import get_g2p

# ✅ Good - check if language supported
try:
    g2p = get_g2p("fr")
    phonemize_ssmd("[Bonjour]{lang='fr'}")
except ValueError:
    print("French not supported")
```

---

## See Also

- [API Documentation](api.md) - Main API functions
- [Span Documentation](spans.md) - Understanding character offsets
- [Examples](../examples/new_api_demo.py) - Complete working examples
