# Advanced Usage

This guide covers advanced features and usage patterns for kokorog2p.

## Prepared text boundary

Semantic preparation is outside KokoroG2P. Prepare written forms in the owning
application or an optional cross-package tool, then pass the result to
`phonemize_prepared()`. Core normalizers may apply only intrinsic typography and
phonological normalization.

## Lexphon provider fallback ownership

Generic eSpeak and Goruut fallback flags configure Lexphon 0.2 providers for migrated
native frontends. The frontends still perform language-specific IPA normalization and
Kokoro vocabulary conversion. `use_cli` affects only the direct compatibility backends,
not Lexphon provider execution.

Provider results carry structured provenance metadata and are excluded from lexical
routing evidence. Provider and Lexphon dictionary data are provisioned explicitly;
KokoroG2P does not download or cache provider results.

## Custom G2P Configuration

### Tri-state spaCy model resolution

The factory distinguishes optional model discovery from required model selection:

- `use_spacy=None` attempts the highest installed and loadable local model for the
  English and French defaults, then falls back to native tokenization.
- `use_spacy=True` requires a loadable local model and raises
  `SpacyModelResolutionError` when resolution fails.
- `use_spacy=False` forces native tokenization. Model arguments are ignored with a
  warning.
- A concrete `spacy_model` or exact `spacy_model_size` is always strict when spaCy is
  enabled.

No path downloads a model. The selected Boolean and concrete package are included in the
G2P cache identity, so changing local model availability cannot reuse an instance with
stale tokenization behavior. Per-span `lang` overrides create language-specific G2P
instances using the same resolution rules.

### Memory-Efficient Loading
### External lexicon provisioning

English and French dictionaries are installed outside KokoroG2P through Lexphon:

```bash
lexphon data install en-us:gold en-gb:gold fr-fr:gold
lexphon data verify en-us:gold en-gb:gold fr-fr:gold
```

The default English and French constructors select the external `gold` asset. Use
`lexicons=()` for a fallback-only instance. There is no English silver tier and no
runtime API for loading or selecting producer-owned assets.

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us")  # requires en-us:gold to be installed
fallback_only = get_g2p("en-us", lexicons=())
```

Runtime lookup is offline. Construction does not fetch catalogs or invoke the Lexphon
CLI. If selected data is missing, the error includes the install and verify commands.

### spaCy Model Selection (English)

English G2P lets you choose which spaCy model to use for POS tagging. This affects
homograph and heteronym disambiguation quality (for example, `lives` noun vs verb).

```python
from kokorog2p.en import EnglishG2P

# Default (recommended balance)
g2p_md = EnglishG2P(use_spacy=True, spacy_model="en_core_web_md")

# Smaller model (lower memory / faster downloads)
g2p_sm = EnglishG2P(use_spacy=True, spacy_model="en_core_web_sm")

# Largest model (highest spaCy English accuracy, highest memory)
g2p_lg = EnglishG2P(use_spacy=True, spacy_model="en_core_web_lg")
```

The same option is also available through `get_g2p()`:

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us", use_spacy=True, spacy_model="en_core_web_md")
```

### Stress Control

Control stress marker output:

```python
from kokorog2p.de import GermanG2P

# Strip stress markers from output
g2p = GermanG2P(
    language="de-de",
    strip_stress=True  # Remove ˈ and ˌ markers
)
```

## Token Inspection

Tokens contain detailed information:

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us", use_spacy=True)
tokens = g2p("I can't believe it!")

for token in tokens:
    # Basic attributes
    print(f"Text: {token.text}")
    print(f"Phonemes: {token.phonemes}")
    print(f"POS tag: {token.tag}")
    print(f"Whitespace: '{token.whitespace}'")

    # Additional metadata
    rating = token.get("rating")  # 5=dictionary, 2=espeak, 0=unknown
    print(f"Rating: {rating}")

    # Check token type
    is_punct = not any(c.isalnum() for c in token.text)
    print(f"Is punctuation: {is_punct}")
```

### Rating System

Tokens have a rating indicating the source of phonemes:

- **5**: User-provided (via OverrideSpan) or gold dictionary (highest quality)
- **4**: Punctuation
- **3**: Lexicon, provider fallback, or rule-based conversion
- **2**: Native language rule conversion (language-specific policy)
- **1**: Reserved for frontend-specific low-confidence output
- **0**: Unknown/failed

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us")
tokens = g2p("Hello xyznotaword!")

for token in tokens:
    rating = token.get("rating", 0)
    if rating == 5:
        print(f"{token.text}: Lexicon quality tier")
    elif rating == 3:
        print(f"{token.text}: Lexicon, provider, or rule-based")
    elif rating == 2:
        print(f"{token.text}: Native rule conversion")
    elif rating == 0:
        print(f"{token.text}: Unknown")
```

## Dictionary Lookup

Direct dictionary access:

```python
from kokorog2p.en import EnglishG2P

g2p = EnglishG2P(language="en-us", lexicons="gold")
phonemes = g2p.lexicon.lookup("hello")
print(phonemes)  # həlˈO

# Check if word is in the externally installed dictionary
if g2p.lexicon.is_known("hello"):
    print("Word is in the gold dictionary")

# POS-aware lookup
phonemes_verb = g2p.lexicon.lookup("read", tag="VB")   # ɹˈid (present)
phonemes_past = g2p.lexicon.lookup("read", tag="VBD")  # ɹˈɛd (past)
```

## German Lexicon

German dictionaries are externally managed by `g2lex-data` and installed explicitly
through Lexphon. KokoroG2P does not bundle or download German dictionary data.

```bash
python -m pip install "kokorog2p[de]"
lexphon data install de-de:gold
lexphon data verify de-de:gold
```

```python
from kokorog2p import get_g2p

g2p = get_g2p("de")
print(g2p.phonemize("Guten Tag"))
```

The runtime uses the installed local store without network access. Install
`de-de:crane`, `de-de:espeak`, `de-de:olaph`, or `de-de:lexhint` before selecting those
names. `lexicons="espeak"` selects the static Lexphon dictionary and is distinct from
`use_espeak_fallback=True`. Use `use_lexicon=False` for fallback-only operation.

## Phoneme Utilities

### Validation

Validate phonemes against Kokoro vocabulary:

```python
from kokorog2p import validate_phonemes, get_vocab

# Check if phonemes are valid
valid = validate_phonemes("hˈɛlO")
print(valid)  # True

invalid = validate_phonemes("xyz123")
print(invalid)  # False

# Get the full vocabulary
vocab = get_vocab("us")
print(f"US vocabulary: {len(vocab)} phonemes")
```

### Conversion

Convert between different phoneme formats:

```python
from kokorog2p import from_espeak, to_espeak

# Convert espeak IPA to Kokoro
espeak_ipa = "həlˈəʊ"
kokoro_phonemes = from_espeak(espeak_ipa, variant="us")
print(kokoro_phonemes)  # hˈɛlO

# Convert Kokoro to espeak IPA
kokoro = "hˈɛlO"
espeak = to_espeak(kokoro, variant="us")
print(espeak)
```

## Vocabulary Encoding

Convert phonemes to IDs for model input:

```python
from kokorog2p import phonemes_to_ids, ids_to_phonemes

# Encode phonemes
phonemes = "hˈɛlO wˈɜɹld"
ids = phonemes_to_ids(phonemes)
print(ids)  # [12, 45, 23, ...]

# Decode back
decoded = ids_to_phonemes(ids)
print(decoded)  # hˈɛlO wˈɜɹld

# Get Kokoro vocabulary
from kokorog2p import get_kokoro_vocab
vocab = get_kokoro_vocab()
print(f"Kokoro has {len(vocab)} tokens")
```

## Quote Handling

kokorog2p provides sophisticated quote handling with support for nested quotes and
automatic conversion to curly quotes.

### Nested Quote Detection

The tokenizer supports two modes for handling quotes:

```python
from kokorog2p import get_g2p

# Default: Bracket-matching mode (supports nesting)
g2p = get_g2p("en-us")
tokens = g2p('He said "She used `backticks` here"')

# Check quote depths
for token in tokens:
    depth = token.quote_depth
    print(f"{token.text}: depth={depth}")
# Output shows nesting: "=1, `=2, `=2, "=1
```

**Bracket-Matching Mode** (default):

- Supports nested quotes when using **different** quote characters
- Maintains a stack to track nesting depth
- Supported quote characters: `"` (double quote), ` `` ` (backtick), `'` (single quote)
- Depth increases with each level of nesting (1 = outermost, 2 = nested once, etc.)

**Important**: Nesting only works with different quote types:

- ✅ **Supported**: `` "outer `inner` text" `` → depths `[1, 2, 2, 1]` (different
  quotes)
- ❌ **NOT supported**: `"level1 "level2""` → depths `[1, 1, 1, 1]` (same quotes
  alternate)

Examples:

```python
from kokorog2p.pipeline.tokenizer import RegexTokenizer

# Create tokenizer with bracket matching (default)
tokenizer = RegexTokenizer(use_bracket_matching=True)

# Simple pair
tokens = tokenizer.tokenize('"hello"', '"hello"')
# Quote depths: [1, 1]

# Nested quotes (different types)
tokens = tokenizer.tokenize('"outer `inner` text"', '"outer `inner` text"')
# Quote depths: [1, 2, 2, 1]

# Multiple separate pairs
tokens = tokenizer.tokenize('"first" and "second"', '"first" and "second"')
# Quote depths: [1, 1, 1, 1]

# Triple nesting (different types)
tokens = tokenizer.tokenize('"a `b \'c\' d` e"', '"a `b \'c\' d` e"')
# Quote depths: [1, 2, 3, 3, 2, 1]
```

**Simple Alternation Mode**:

For simpler use cases without nesting support:

```python
from kokorog2p.pipeline.tokenizer import RegexTokenizer

# Disable bracket matching for simple alternation
tokenizer = RegexTokenizer(use_bracket_matching=False)

# First quote opens (depth 1), second closes (depth 0)
tokens = tokenizer.tokenize('"hello" world', '"hello" world')
# Quote depths: [1, 0, 0]
```

### Curly Quote Conversion

The tokenizer automatically converts straight quotes to curly quotes based on nesting
depth:

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us")

# Straight quotes converted to curly quotes
tokens = g2p('She said "hello"')

# First quote becomes left curly ("), last becomes right curly (")
quote_chars = [t.text for t in tokens if t.text in ('"', '"')]
print(quote_chars)  # ['"', '"']
```

**Conversion Rules**:

- Opening quotes (depth increases) → left curly quote `"` (U+201C)
- Closing quotes (depth decreases) → right curly quote `"` (U+201D)
- Backticks follow the same pattern as double quotes
- Single quotes use standard apostrophe `'` (U+0027)

### Quote Depth in Custom Processing

Access quote depth for custom processing:

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us")
tokens = g2p('He said "She whispered `quietly`"')

# Analyze quote nesting
for token in tokens:
    if token.quote_depth > 0:
        indent = "  " * (token.quote_depth - 1)
        print(f"{indent}[{token.quote_depth}] {token.text}")
```

Output shows nesting structure:

```text
[1] "
[1] She
[1] whispered
  [2] `
  [2] quietly
  [2] `
[1] "
```

## Punctuation Handling

### Automatic Normalization

kokorog2p automatically normalizes punctuation variants to ensure consistency with
Kokoro TTS vocabulary:

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us")

# Ellipsis variants → single ellipsis character (…)
tokens = g2p("Wait... really?")      # ... → …
tokens = g2p("Wait. . . really?")    # . . . → …
tokens = g2p("Wait.. really?")       # .. → …
tokens = g2p("Wait…really?")         # … preserved

# Dash variants → em dash (—)
tokens = g2p("Wait - what?")         # spaced hyphen → em dash
tokens = g2p("Wait -- what?")        # double hyphen → em dash
tokens = g2p("Wait – what?")         # en dash → em dash
tokens = g2p("Wait — what?")         # em dash preserved
tokens = g2p("Wait ― what?")         # horizontal bar → em dash
tokens = g2p("Wait ‒ what?")         # figure dash → em dash
tokens = g2p("Wait − what?")         # minus sign → em dash

# Compound words preserve hyphens (no normalization)
tokens = g2p("well-known")           # hyphen removed, words joined
tokens = g2p("state-of-the-art")     # hyphens removed, words joined
```

**Normalization Rules:**

- **Ellipsis**: All variants (`...`, `. . .`, `..`, `....`) → `…` (U+2026)

- **Em dash**: All dash types when spaced (`-`, `--`, `–`, `—`, `―`, `‒`, `−`) → `—`
  (U+2014)

- **Hyphens in compound words**: Preserved during tokenization, then removed in phoneme
  output

- **Apostrophes**: All variants (`'`, `'`, `'`, ` , ``´ `, etc.) → `'` (U+0027)

### Manual Normalization

Control punctuation normalization manually:

```python
from kokorog2p import normalize_punctuation, filter_punctuation

# Normalize to Kokoro punctuation
text = "Hello... world!!!"
normalized = normalize_punctuation(text)
print(normalized)  # Hello. world!

# Filter out non-Kokoro punctuation
phonemes = "hˈɛlO… wˈɜɹld‼"
filtered = filter_punctuation(phonemes)
print(filtered)  # hˈɛlO. wˈɜɹld!

# Check if punctuation is valid
from kokorog2p import is_kokoro_punctuation
print(is_kokoro_punctuation("!"))   # True
print(is_kokoro_punctuation("…"))   # True (normalized automatically)
print(is_kokoro_punctuation("‼"))   # False
```

## Word Mismatch Detection

Detect mismatches between input text and phoneme output:

```python
from kokorog2p import detect_mismatches

text = "Hello world!"
phonemes = "hɛlO wɜɹld !"

mismatches = detect_mismatches(text, phonemes)

for mismatch in mismatches:
    print(f"Position {mismatch.position}:")
    print(f"  Input word: {mismatch.input_word}")
    print(f"  Output word: {mismatch.output_word}")
    print(f"  Type: {mismatch.type}")
```

## Semantic preparation

Number, currency, date, abbreviation, and unit expansion are not configurable G2P
features. Prepare these forms before calling `phonemize_prepared()`; the core preserves
the supplied text and applies only phonological/model normalization.

## Custom Backend Selection

Choose specific backends:

```python
from kokorog2p import get_g2p

# Use espeak backend
g2p_espeak = get_g2p("en-us", backend="espeak")

# Use goruut backend (if installed)
g2p_goruut = get_g2p("en-us", backend="goruut")
```

### Direct Backend Access

```python
from kokorog2p.backends.espeak import EspeakBackend

# Create espeak backend
backend = EspeakBackend(language="en-us")

# Phonemize a word
phonemes = backend.phonemize("hello")
print(phonemes)
```

## Caching and Performance

### Managing Cache

```python
from kokorog2p import get_g2p, clear_cache

# G2P instances are cached by language and settings
g2p1 = get_g2p("en-us", use_spacy=True)
g2p2 = get_g2p("en-us", use_spacy=True)
assert g2p1 is g2p2  # Same instance

# Different settings = different cache entry
g2p3 = get_g2p("en-us", use_spacy=False)
assert g2p1 is not g2p3  # Different instance

# Lexicon selection also affects caching
g2p4 = get_g2p("en-us", lexicons=())
assert g2p1 is not g2p4  # Different instance (fallback-only mode)

g2p5 = get_g2p("en-us", lexicons="gold")
assert g2p1 is not g2p5  # Different explicit selection

# Clear cache when needed
clear_cache()
```

### Batch Processing

For best performance when processing many texts:

```python
from kokorog2p import get_g2p

# Create instance once
g2p = get_g2p("en-us")

texts = ["Hello", "World", "This", "Is", "Fast"]

# Process many texts with same instance
all_tokens = []
for text in texts:
    tokens = g2p(text)
    all_tokens.append(tokens)
```

## Custom Phoneme Filtering

Filter phonemes for specific use cases:

```python
from kokorog2p import get_g2p, validate_for_kokoro, filter_for_kokoro

g2p = get_g2p("en-us")
tokens = g2p("Hello world!")

phoneme_str = " ".join(t.phonemes for t in tokens if t.phonemes)

# Validate for Kokoro
is_valid = validate_for_kokoro(phoneme_str)

# Filter to keep only valid Kokoro phonemes
filtered = filter_for_kokoro(phoneme_str)
print(filtered)
```

## Explicit language spans

For mixed-language documents, the application must identify foreign spans and supply
their language explicitly. Use `OverrideSpan` or annotation `language` metadata with the
prepared text. KokoroG2P does not provide generic language detection or segmentation.

## Error Handling

kokorog2p provides robust error handling to help you debug issues, especially in CI/CD
environments.

### Strict Mode (Default)

By default, kokorog2p uses **strict mode** (`strict=True`), which raises clear
exceptions when backend initialization or phonemization fails:

```python
from kokorog2p import get_g2p

# Strict mode is the default
g2p = get_g2p("en-us", backend="espeak", strict=True)

try:
    result = g2p.phonemize("test")
except RuntimeError as e:
    # Get detailed error message about what went wrong
    print(f"Error: {e}")
    # Example: "Espeak backend validation failed. Please ensure espeak-ng
    # is properly installed and voice 'en-us' is available."
```

**Benefits of strict mode:**

- Catches configuration issues immediately
- Provides actionable error messages
- Prevents silent failures in CI/CD pipelines
- Recommended for production use

### Lenient Mode (Backward Compatible)

For backward compatibility with older versions (< 0.4.0) that silently failed, you can
use **lenient mode** (`strict=False`):

```python
from kokorog2p import get_g2p

# Lenient mode logs errors but doesn't raise exceptions
g2p = get_g2p("en-us", backend="espeak", strict=False)

result = g2p.phonemize("test")
# If espeak fails:
# - Error is logged to Python's logging system
# - Returns empty string "" instead of raising exception
# - Allows your application to continue running
```

**When to use lenient mode:**

- Migrating from older versions (< 0.4.0)
- Non-critical applications where empty results are acceptable
- When you have your own error handling logic

### Common Error Scenarios

**espeak-ng not installed:**

```python
# Strict mode (default)
g2p = get_g2p("en-us", backend="espeak")
# RuntimeError: Espeak backend validation failed. Please ensure espeak-ng
# is properly installed...

# Solution: Install espeak-ng
# Ubuntu/Debian: sudo apt-get install espeak-ng
# macOS: brew install espeak
# Windows: Download from https://github.com/espeak-ng/espeak-ng/releases
```

**Invalid voice:**

```python
from kokorog2p.espeak_g2p import EspeakOnlyG2P

g2p = EspeakOnlyG2P(language="xx-invalid")
# RuntimeError: Espeak backend validation failed...voice 'xx-invalid' is unavailable
```

**CI/CD Best Practices:**

```python
import logging

# Configure logging to see error details
logging.basicConfig(level=logging.INFO)

# Use strict mode in CI to catch issues early (this is the default)
g2p = get_g2p("en-us", backend="espeak", strict=True)

# Your CI will fail with clear error messages if there are issues
```

**Handling missing dependencies:**

```python
from kokorog2p import get_g2p

try:
    # This might fail if Chinese dependencies not installed
    g2p = get_g2p("zh")
    tokens = g2p("你好")
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install kokorog2p[zh]")

try:
    # This might fail if spaCy model not downloaded
    g2p = get_g2p("en-us", use_spacy=True)
except OSError as e:
    print("spaCy model not found")
    print("Download with: python -m spacy download en_core_web_md")
```

### Configuring with Different Backends

The `strict` parameter works with all backends:

```python
from kokorog2p import get_g2p

# Espeak backend with strict mode
g2p_espeak = get_g2p("en-us", backend="espeak", strict=True)

# Goruut backend with strict mode
g2p_goruut = get_g2p("en-us", backend="goruut", strict=True)

# Dictionary-based with fallback (strict controls fallback/init errors)
g2p_dict = get_g2p(
    "en-us",
    backend="kokorog2p",
    use_espeak_fallback=True,
    strict=True  # Affects fallback initialization and errors
)
```

## Next Steps

- See {doc}`api/core` for detailed API reference
- Check {doc}`languages` for language-specific features
- Read {doc}`phonemes` to understand the phoneme inventory

## Selecting named lexicons

Use `available_lexicons(language)` to inspect registered names and pass `lexicons` to
`get_g2p` or `phonemize`. A sequence is an ordered precedence stack. English and French
expose only the external `gold` selection; `lexicons=()` disables dictionary lookup.

For German, `available_lexicons("de")` returns `("gold", "crane", "espeak", "olaph")`.
`gold` remains the implicit default. Explicit order controls collisions, and runtime
pronunciation selection is offline. `espeak` is a static Lexphon dictionary and is distinct
from the optional `use_espeak_fallback=True` backend.
Unsupported source IPA fails closed and may fall through to configured fallback. See
{doc}`api/german` for provenance and examples.
