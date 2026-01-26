[![PyPI - Version](https://img.shields.io/pypi/v/kokorog2p)](https://pypi.org/project/kokorog2p/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kokorog2p)
![PyPI - Downloads](https://img.shields.io/pypi/dm/kokorog2p)
[![codecov](https://codecov.io/gh/holgern/kokorog2p/graph/badge.svg?token=iCHXwbjAXG)](https://codecov.io/gh/holgern/kokorog2p)

# kokorog2p

A unified multi-language G2P (Grapheme-to-Phoneme) library for Kokoro TTS.

kokorog2p converts text to phonemes optimized for the Kokoro text-to-speech system. It
provides:

- **Multi-language support**: English (US/GB), German, French, Italian, Spanish,
  Portuguese (Brazilian), Czech, Chinese, Japanese, Korean, Hebrew
- **Mixed-language preprocessing**: Detect languages for per-word language switching
- **Dictionary-based lookup** with comprehensive lexicons
  - English: 179k+ entries (gold tier), 187k+ silver tier (both loaded by default)
  - German: 738k+ entries from Olaph/IPA-Dict
  - French: Gold-tier dictionary
  - Portuguese (Brazilian): Rule-based with affrication support
  - Italian, Spanish: Rule-based with small lexicons
  - Czech, Chinese, Japanese, Korean, Hebrew: Rule-based and specialized engines
- **Flexible memory usage**: Control dictionary loading with `load_silver` and
  `load_gold` parameters
  - Disable silver: saves ~22-31 MB
  - Disable both: saves ~50+ MB for ultra-fast initialization
- **espeak-ng integration** as a fallback for out-of-vocabulary words
- **Automatic IPA to Kokoro phoneme conversion**
- **Automatic punctuation normalization** (ellipsis, dashes, apostrophes)
- **Context-aware abbreviation expansion** (e.g., "St." → "Street" or "Saint" based on
  context)
- **Number and currency handling** for supported languages
- **Stress assignment** based on linguistic rules

## Installation

```bash
# Core package (no dependencies)
pip install kokorog2p

# With English support
pip install kokorog2p[en]

# With German support
pip install kokorog2p[de]

# With French support
pip install kokorog2p[fr]

# With multilang preprocessing support
pip install kokorog2p[mixed]

# With espeak-ng backend
pip install kokorog2p[espeak]

# With goruut backend
pip install kokorog2p[goruut]

# Full installation (all languages and backends)
pip install kokorog2p[all]
```

## Quick Start

```python
from kokorog2p import phonemize

# English (US)
phonemes = phonemize("Hello world!", language="en-us")
print(phonemes)  # həlˈoʊ wˈɜːld!

# British English
phonemes = phonemize("Hello world!", language="en-gb")
print(phonemes)  # həlˈəʊ wˈɜːld!

# German
phonemes = phonemize("Guten Tag!", language="de")
print(phonemes)  # ɡuːtn̩ taːk!

# French
phonemes = phonemize("Bonjour!", language="fr")
print(phonemes)

# Italian
phonemes = phonemize("Ciao, come stai?", language="it")
print(phonemes)  # ʧiao, kome stai?

# Spanish
phonemes = phonemize("¡Hola! ¿Cómo estás?", language="es")
print(phonemes)  # !ola! ?koˈmo estaˈs?

# Chinese
phonemes = phonemize("你好", language="zh")
print(phonemes)

# Korean
phonemes = phonemize("안녕하세요", language="ko")
print(phonemes)

# Hebrew (requires phonikud package)
phonemes = phonemize("שָׁלוֹם", language="he")
print(phonemes)
```

## Advanced Usage

```python
from kokorog2p import get_g2p

# English with default settings (gold + silver dictionaries)
g2p_en = get_g2p("en-us", use_espeak_fallback=True)
tokens = g2p_en("The quick brown fox jumps over the lazy dog.")
for token in tokens:
    print(f"{token.text} → {token.phonemes}")

# Memory-optimized: disable silver (~22-31 MB saved, ~400-470 ms faster init)
g2p_fast = get_g2p("en-us", load_silver=False)
tokens = g2p_fast("Hello world!")

# Ultra-fast initialization: disable both gold and silver (~50+ MB saved)
# Falls back to espeak for all words
g2p_minimal = get_g2p("en-us", load_silver=False, load_gold=False)
tokens = g2p_minimal("Hello world!")

# Different dictionary configurations
# load_gold=True, load_silver=True:  Maximum coverage (default)
# load_gold=True, load_silver=False: Common words only, faster
# load_gold=False, load_silver=True: Extended vocabulary only (unusual)
# load_gold=False, load_silver=False: No dictionaries, espeak only (fastest)

# Error handling with strict mode (default: strict=True)
# Strict mode raises clear exceptions for debugging issues
g2p_strict = get_g2p("en-us", backend="espeak", strict=True)
# If espeak fails: RuntimeError with detailed error message

# Lenient mode for backward compatibility (logs errors, returns empty results)
g2p_lenient = get_g2p("en-us", backend="espeak", strict=False)
# If espeak fails: logs error, returns empty string (no exception)

# Automatic punctuation normalization
g2p = get_g2p("en-us")
tokens = g2p("Wait... really?")       # ... → … (ellipsis)
tokens = g2p("Wait - what?")          # - → — (em dash when spaced)
tokens = g2p("don't worry")           # All apostrophe variants → '
tokens = g2p("well-known topic")      # Hyphens in compounds preserved

# Context-aware abbreviation expansion (English)
# "St." intelligently expands to "Street" or "Saint" based on context
g2p = get_g2p("en-us", expand_abbreviations=True, enable_context_detection=True)
tokens = g2p("123 Main St.")          # St. → Street (house number pattern)
tokens = g2p("St. Patrick's Day")     # St. → Saint (saint name recognized)
tokens = g2p("Visit St. Louis")       # St. → Saint (city name recognized)
tokens = g2p("Born in 1850, St. Peter")  # St. → Saint (distant number ignored)

# German with lexicon and number handling
g2p_de = get_g2p("de")
tokens = g2p_de("Es kostet 42 Euro.")
for token in tokens:
    print(f"{token.text} → {token.phonemes}")

# French with fallback support
g2p_fr = get_g2p("fr", use_espeak_fallback=True)
tokens = g2p_fr("C'est magnifique!")
for token in tokens:
    print(f"{token.text} → {token.phonemes}")
```

## Error Handling and Debugging

kokorog2p provides robust error handling to help you debug issues, especially in CI/CD
environments.

### Strict Mode (Default, Recommended)

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

**Benefits:**

- Catches configuration issues immediately
- Provides actionable error messages
- Prevents silent failures in CI/CD pipelines
- Recommended for production use

### Lenient Mode (Backward Compatible)

For backward compatibility with older versions that silently failed, you can use
**lenient mode** (`strict=False`):

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

# Use strict mode in CI to catch issues early
g2p = get_g2p("en-us", backend="espeak", strict=True)

# Your CI will fail with clear error messages if there are issues
```

## Pipeline-Friendly API (NEW)

kokorog2p now provides a **span-based phonemization API** designed for integration with
text processing pipelines. This API uses character offsets for deterministic override
application and supports per-token language switching.

### Key Features

- **Offset-based alignment**: Handles duplicate words correctly (e.g., "the cat the
  dog")
- **Direct token ID output**: Ready for model input without post-processing
- **Per-token language switching**: Mix languages within a single sentence
- **Comprehensive warnings**: Debug alignment issues with detailed feedback
- **Backward compatible**: Legacy word-based alignment still available

### Quick Example

```python
from kokorog2p import phonemize, OverrideSpan

# Simple phonemization
result = phonemize("Hello world!")
print(result.phonemes)    # 'həlˈoʊ wˈɜɹld!'
print(result.token_ids)   # [50, 83, 54, ...]

# Handle duplicate words with different pronunciations
text = "the cat the dog"
overrides = [
    OverrideSpan(0, 3, {"ph": "ðə"}),   # First "the"
    OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the"
]
result = phonemize(text, overrides=overrides)
# Both overrides applied correctly!

# Language switching within text
text = "Hello Bonjour world"
overrides = [OverrideSpan(6, 13, {"lang": "fr"})]
result = phonemize(text, lang="en-us", overrides=overrides)
# "Bonjour" phonemized with French G2P
```

### Documentation

- **[API Reference](docs/api.md)** - Complete function documentation
- **[Span Guide](docs/spans.md)** - Understanding character offsets and alignment
- **[Marker Helper](docs/markers.md)** - Convenient marker-based override syntax
- **[Examples](examples/)** - Working code examples

### Use Cases

✅ **Pipeline Integration**: Preserve offsets through preprocessing stages ✅
**Duplicate Handling**: Apply different pronunciations to repeated words ✅
**Multi-language**: Switch languages per-word within sentences ✅ **Model Input**: Get
token IDs directly without manual conversion ✅ **Debugging**: Comprehensive warnings
for alignment issues

## Mixed-Language Preprocessing

kokorog2p provides a standalone multilang preprocessor that detects word-level languages
with `lingua-language-detector` and generates `OverrideSpan` objects for per-word
language switching.

### Installation

```bash
# Install with language detection support
pip install kokorog2p[mixed]

# Or install lingua directly
pip install lingua-language-detector
```

### Basic Usage

```python
from kokorog2p import phonemize
from kokorog2p.multilang import preprocess_multilang

text = "Ich gehe zum Meeting. Let's discuss the Roadmap!"
clean_text, overrides = preprocess_multilang(
    text,
    default_language="de",
    allowed_languages=["de", "en-us"],
)
result = phonemize(clean_text, lang="de", overrides=overrides)
```

### Confidence Threshold

```python
from kokorog2p.multilang import preprocess_multilang

annotated = preprocess_multilang(
    "Hello! Bonjour! Hola!",
    default_language="en-us",
    allowed_languages=["en-us", "de", "fr", "es"],
    confidence_threshold=0.6,
)
```

### Limitations

- Very short words (<3 chars) keep the default language
- Proper nouns may be misdetected
- Requires `lingua-language-detector` installation
- Detected language must be in `allowed_languages`

### Example: Technical Documentation

```python
from kokorog2p import phonemize_to_result
from kokorog2p.multilang import preprocess_multilang

text = """
Das System verwendet Machine Learning für die Performance-Optimierung.
Der Workflow ist sehr efficient durch das Caching.
"""

clean_text, overrides = preprocess_multilang(
    text,
    default_language="de",
    allowed_languages=["de", "en-us"],
)
result = phonemize_to_result(clean_text, lang="de", overrides=overrides)
print(result.phonemes)
```

## Supported Languages

| Language     | Code    | Dictionary Size                   | Number Support | Notation | Status     |
| ------------ | ------- | --------------------------------- | -------------- | -------- | ---------- |
| English (US) | `en-us` | 179k gold + 187k silver (default) | ✓              | IPA      | Production |
| English (GB) | `en-gb` | 173k gold + 220k silver (default) | ✓              | IPA      | Production |
| German       | `de`    | 738k+ entries (gold)              | ✓              | IPA      | Production |
| French       | `fr`    | Gold dictionary                   | ✓              | IPA      | Production |
| Italian      | `it`    | Rule-based + small lexicon        | -              | IPA      | Production |
| Spanish      | `es`    | Rule-based + small lexicon        | -              | IPA      | Production |
| Czech        | `cs`    | Rule-based                        | -              | IPA      | Production |
| Chinese      | `zh`    | pypinyin + ZHFrontend             | ✓              | Zhuyin   | Production |
| Japanese     | `ja`    | pyopenjtalk                       | -              | IPA      | Production |
| Korean       | `ko`    | g2pK rule-based                   | ✓              | IPA      | Production |
| Hebrew       | `he`    | phonikud-based (requires nikud)   | -              | IPA      | Production |

**Note:** Both gold and silver dictionaries are loaded by default for English. You can:

- Use `load_silver=False` to save ~22-31 MB (gold only, ~179k entries)
- Use `load_gold=False, load_silver=False` to save ~50+ MB (espeak fallback only)

**Chinese Note:** Chinese G2P uses Zhuyin (Bopomofo) phonetic notation for Kokoro TTS
compatibility. Arabic numerals are automatically converted to Chinese (e.g., "123" → "一
百二十三"). For version 1.1 (recommended):

```python
from kokorog2p.zh import ChineseG2P
g2p = ChineseG2P(version="1.1")  # Uses ZHFrontend with Zhuyin notation
```

**Spanish Note:** Spanish G2P supports both European and Latin American dialects:

```python
from kokorog2p.es import SpanishG2P

# European Spanish (with theta θ)
g2p_es = SpanishG2P(dialect="es")
print(g2p_es.phonemize("zapato"))  # θapato

# Latin American Spanish (seseo: θ→s)
g2p_la = SpanishG2P(dialect="la")
print(g2p_la.phonemize("zapato"))  # sapato
```

Key features: R trill/tap distinction (pero vs perro), palatals (ñ, ll, ch), jota sound
(j), and proper stress marking.

**Korean Note:** Korean G2P works out of the box with rule-based phonemization. For
improved accuracy with morphological analysis, install MeCab:

```bash
pip install mecab-python3
```

**Hebrew Note:** Hebrew G2P requires the phonikud package for phonemization:

```bash
pip install kokorog2p[he]
# or directly:
pip install phonikud
```

Note: Hebrew text should include nikud (diacritical marks) for accurate phonemization.

## Phoneme Inventory

kokorog2p uses Kokoro's 45-phoneme vocabulary:

### Vowels (US)

- Monophthongs: `æ ɑ ə ɚ ɛ ɪ i ʊ u ʌ ɔ`
- Diphthongs: `aɪ aʊ eɪ oʊ ɔɪ`

### Consonants

- Stops: `p b t d k ɡ`
- Fricatives: `f v θ ð s z ʃ ʒ h`
- Affricates: `tʃ dʒ`
- Nasals: `m n ŋ`
- Liquids: `l ɹ`
- Glides: `w j`

### Suprasegmentals

- Primary stress: `ˈ`
- Secondary stress: `ˌ`

## License

Apache2 License - see [LICENSE](LICENSE) for details.

## Credits

kokorog2p consolidates functionality from:

- [misaki](https://github.com/hexgrad/misaki) - G2P engine for Kokoro TTS
- [phonemizer](https://github.com/bootphon/phonemizer) - espeak-ng wrapper
