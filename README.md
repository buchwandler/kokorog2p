[![PyPI - Version](https://img.shields.io/pypi/v/kokorog2p)](https://pypi.org/project/kokorog2p/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/kokorog2p)
![PyPI - Downloads](https://img.shields.io/pypi/dm/kokorog2p)
[![codecov](https://codecov.io/gh/buchwandler/kokorog2p/graph/badge.svg?token=iCHXwbjAXG)](https://codecov.io/gh/buchwandler/kokorog2p)

# kokorog2p

A unified multi-language G2P (Grapheme-to-Phoneme) library for Kokoro TTS.

kokorog2p converts text to phonemes optimized for the Kokoro text-to-speech system. It
provides:

- **Multi-language support**: English (US/GB), German, French, Italian, Spanish,
  Portuguese (Brazilian), Czech, Chinese, Japanese, Korean, Hebrew, Vietnamese, Swedish,
  Thai (optional), Russian (optional), Kazakh (optional)
- **Native Vietnamese frontend**: Pure-Python Northern/Hanoi `vi-vn` profile with six
  named tones
- **Native Swedish frontend**: Pure-Python deterministic rules with no runtime lexicon;
  external TSV benchmarking is development-only
- **Native Thai frontend**: Optional TLTK/PyThaiNLP frontend targeting
  `wayu-kokoro-thai-v1`; Latin phrases use lazy EnglishG2P
- **Native Russian frontend**: Optional RUAccent contextual stress, ё restoration,
  source-aligned tokens, and stock Kokoro 1.0 labels
- **Native Kazakh frontend**: eSpeak-NG `kk` raw IPA profile with Kokoro vocabulary
  validation
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
- **Optional highest-available spaCy model selection** for supported POS-tagging
  languages (`trf` > `lg` > `md` > `sm`), with strict `use_spacy=True`, `spacy_model`,
  and `spacy_model_size` requests and no model downloads
- **Number and currency handling** for supported languages
- **German structured normalization** for safe abbreviations, German decimals and
  thousands separators, dates, times, temperatures, EUR amounts, and number-dependent
  units (`1 Std.` → `eine Stunde`, `2 kg` → `zwei Kilogramm`)
- **Stress assignment** based on linguistic rules

## Text-preparation architecture

```text
abbr2words → lexical abbreviation recognition and customization
spokenform → authoritative written text to spoken semantic preparation
kokorog2p  → language routing, spans, overrides, tokenization, G2P, and phonemes
```

For Spokenform-supported languages, kokorog2p passes the original source syntax to
Spokenform first. Once Spokenform accepts a source span, its replacement text and source
provenance are preserved literally; kokorog2p only performs model-specific punctuation
cleanup, tokenization, G2P, and phoneme conversion. PolyNorm remains an upstream
Spokenform benchmark, while kokorog2p verifies compact downstream handoffs rather than
copying that corpus.

All 17 supported language families now use the same Spokenform preparation boundary:
`en`, `de`, `fr`, `es`, `it`, `pt`, `cs`, `vi`, `ko`, `he`, `zh`, `ja`, `ar`, `sv`,
`th`, `ru`, and `kk`. `abbr2words` remains the registry implementation behind the
Spokenform customization facade; KokoroG2P retains language routing, spans, overrides,
typography, tokenization, G2P, and phonemes. Prepared input is passed directly to the
backend pronunciation layer, with only model-specific sanitation applied.

For example, the released Spokenform 0.3.1 profile prepares a contextual countdown as
`three - two - one`; KokoroG2P then maps that generic segment boundary to two model em
dashes. KokoroG2P does not recognize countdown semantics itself.

## Installation

```bash
# Core package (includes Spokenform semantic preparation)
pip install kokorog2p

# With English support
pip install kokorog2p[en]

# With German support
pip install kokorog2p[de]

# With French support
pip install kokorog2p[fr]

# Thai support (optional TLTK and PyThaiNLP)
pip install "kokorog2p[th]"
# Russian support (optional RUAccent and eSpeak)
pip install "kokorog2p[ru]"

# Kazakh support (eSpeak-NG voice kk)
pip install "kokorog2p[kk]"
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
phonemes = phonemize("Hello world!", language="en-us").phonemes
print(phonemes)  # həlˈoʊ wˈɜːld!

# British English
phonemes = phonemize("Hello world!", language="en-gb").phonemes
print(phonemes)  # həlˈəʊ wˈɜːld!

# German
phonemes = phonemize("Guten Tag!", language="de").phonemes
print(phonemes)  # ɡuːtn̩ taːk!

# French
phonemes = phonemize("Bonjour!", language="fr").phonemes
print(phonemes)

# Italian
phonemes = phonemize("Ciao, come stai?", language="it").phonemes
print(phonemes)  # ʧiao, kome stai?

# Spanish
phonemes = phonemize("¡Hola! ¿Cómo estás?", language="es").phonemes
print(phonemes)  # !ola! ?koˈmo estaˈs?

# Chinese
phonemes = phonemize("你好", language="zh").phonemes
print(phonemes)

# Korean
phonemes = phonemize("안녕하세요", language="ko").phonemes
print(phonemes)


- **Vietnamese** (native Northern/Hanoi profile)

# Hebrew (requires phonikud package)
phonemes = phonemize("שָׁלוֹם", language="he").phonemes
print(phonemes)
```

- **Swedish** (native deterministic rules)

```python
from kokorog2p import get_g2p
g2p_sv = get_g2p("sv")
print(g2p_sv("Hej världen!"))
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

# Configure spaCy model selection for English POS tagging. With use_spacy=None,
# the highest installed loadable tier is selected automatically; no model falls
# back to native tokenization. use_spacy=True makes model resolution required.
g2p_auto = get_g2p("en-us", use_spacy=True)

# Select an exact tier (never falls back if it is not installed)
g2p_size = get_g2p("en-us", use_spacy=True, spacy_model_size="md")
g2p_md = get_g2p("en-us", use_spacy=True, spacy_model="en_core_web_md")

# Lower memory / faster download
g2p_sm = get_g2p("en-us", use_spacy=True, spacy_model="en_core_web_sm")

# Higher memory / explicit large spaCy English model
g2p_lg = get_g2p("en-us", use_spacy=True, spacy_model="en_core_web_lg")

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

## Stable Pipeline Span API

kokorog2p now provides a **span-based phonemization API** designed for integration with
text processing pipelines. This API uses character offsets for deterministic override
application and supports per-token language switching.

### Written versus prepared input

Use `phonemize()` for ordinary written text; kokorog2p owns written-to-spoken semantic
preparation and G2P:

```python
from kokorog2p import phonemize

result = phonemize("Prof. Klein braucht 1 kg.", language="de")
```

If the caller already owns preparation, use the explicit prepared-input path:

```python
from spokenform import prepare_for_kokorog2p
from kokorog2p import phonemize_prepared

prepared = prepare_for_kokorog2p("Prof. Klein braucht 1 kg.", language="de")
result = phonemize_prepared(prepared.spoken_text, language="de")
```

`phonemize_prepared()` skips Spokenform and written-to-spoken semantic expansion, while
retaining tokenization, G2P/backend normalization, Kokoro model punctuation handling,
overrides, phonemes, and token IDs. Its token and override offsets refer directly to the
supplied prepared text. Do not pass arbitrary written text when you expect number, date,
unit, currency, or abbreviation expansion; the caller owns that preparation step.

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
result = phonemize(text, language="en-us", overrides=overrides)
# "Bonjour" phonemized with French G2P
```

### SSMD + phrasplit integration

SSMD and phrasplit both expose zero-based, half-open offsets in their cleaned text.
kokorog2p accepts those objects structurally, so the packages remain optional:

```python
import phrasplit
import ssmd

from kokorog2p import phonemize
from kokorog2p.integrations import overrides_for_segment, overrides_from_ssmd

source = "Say [tomato]{ipa='təˈmeɪtoʊ'}."
parsed = ssmd.parse_spans(source)
overrides = overrides_from_ssmd(parsed.annotations)
segments = phrasplit.split_with_offsets(
    parsed.clean_text, mode="sentence", language="en", use_spacy=None
)

results = []
for segment in segments:
    assert parsed.clean_text[segment.char_start:segment.char_end] == segment.text
    results.append(
        phonemize(
            segment.text,
            language="en-us",
            overrides=overrides_for_segment(
                segment.char_start, segment.char_end, overrides
            ),
            use_spacy=None,
        )
    )
```

`ipa` attributes are normalized to kokorog2p's `ph` override. X-SAMPA is rejected
explicitly unless an application performs a tested conversion first. Always rebase
document-level SSMD spans before phonemizing individual sentence segments; do not align
duplicate sentences by searching for their text.

`use_spacy=None` tries a local model and falls back without downloading. Use
`use_spacy=True`, a concrete `spacy_model`, or `spacy_model_size` when a model is
required; those requests raise a `SpacyModelResolutionError` if unavailable.

Tested compatibility targets are phrasplit 0.3.4 and SSMD 0.8.0 when those packages are
installed in the integration environment.

### Documentation

- **[API Reference](docs/api/core.md)** - Complete function documentation
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
result = phonemize(clean_text, language="de", overrides=overrides)
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
| Vietnamese   | `vi-vn` | Native rule-based Northern/Hanoi  | -              | IPA-like | Production |
| Swedish      | `sv-se` | Native rule-based                 | -              | IPA      | Production |
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

## Russian

Russian support is a native, source-aligned frontend. It uses lazy contextual stress
when RUAccent is installed, supports explicit combining-acute input, and applies Russian
reduction and orthoepy transforms against the stock Kokoro 1.0 vocabulary. Install
`kokorog2p[ru]`; see [Russian API](docs/api/russian.md) and
[Russian provenance](docs/ru/PROVENANCE.md).

## Kazakh

Kazakh (`kk`) uses eSpeak-NG voice `kk` as its pronunciation engine. The native frontend
preserves raw non-English IPA semantics, applies only generic Kokoro compatibility
transforms, and validates output against the stock Kokoro 1.0 vocabulary. Install
`kokorog2p[kk]`.

The upstream Kazakh voice is currently marked `testing`, so pronunciation quality
follows the installed eSpeak-NG release. See [Kazakh API](docs/api/kazakh.md) and
[Kazakh provenance](docs/kk/PROVENANCE.md).

## Arabic MSA

Native Arabic support targets Modern Standard Arabic with the Nabra-compatible
`nabra-82m-v0.1` profile. Already-vocalized input works without optional CAMeL data:

```python
from kokorog2p import phonemize
result = phonemize(
    "مَرْحَبًا بِكَ؟",
    language="ar",
    g2p_options={"diacritizer": "none"},
)
```

Install `kokorog2p[ar]` for the Arabic eSpeak path. The optional
`kokorog2p[ar-diacritize]` extra enables CAMeL integration, but its MSA data must be
provisioned separately and is never downloaded automatically. See
[Arabic API](docs/api/arabic.md) for MSA scope, source offsets, and model-ID caveats.

## Thai

Thai support is an optional native TLTK/PyThaiNLP frontend. It supports the aliases
`th`, `th-th`, `tha`, and `thai`, preserves Thai combining marks, recovers failed engine
chunks with diagnostics, and uses lazy EnglishG2P for Latin phrases.

The frontend targets `wayu-kokoro-thai-v1`; low tone `˩` is token ID 7 in that isolated
vocabulary profile. See [Thai API](docs/api/thai.md) and
[Thai provenance](docs/th/PROVENANCE.md).

## License

Apache2 License - see [LICENSE](LICENSE) for details.

## Credits

kokorog2p consolidates functionality from:

- [misaki](https://github.com/hexgrad/misaki) - G2P engine for Kokoro TTS
- [phonemizer](https://github.com/bootphon/phonemizer) - espeak-ng wrapper

## Named lexicons

Canonical sources stay outside the importable package; installed lookups use only
generated, verified assets:

```text
lexicons/sources/                  # repository/release sources
kokorog2p/lexicons/data/*.g2lex    # packaged runtime assets
```

List and select named lexicons with:

```python
from kokorog2p import available_lexicons, get_g2p, lexicon_info

available_lexicons("en-us")  # ("gold", "silver")
lexicon_info("en-us", "gold")
g2p = get_g2p("en-us", lexicons=("gold", "silver"))
```

German also provides an opt-in Crane/Wiktionary dictionary:

```python
available_lexicons("de")  # ("gold", "crane")
get_g2p("de")  # compatibility default: gold only
get_g2p("de", lexicons="crane")
get_g2p("de", lexicons=("gold", "crane"))
```

`crane` preserves source spellings and ordered pronunciation variants. The explicit
selection order defines collision precedence. Crane data is CC BY-SA 4.0 with
attribution to German Wiktionary contributors; it is not Apache-licensed. Runtime uses
the bundled `.g2lex` asset and does not access the network.

Consumer-specific pronunciation-quality experiments live under `benchmarks/`, separate
from the G2Lex runtime. The German source benchmark accepts explicit local G2Lex assets
or source files and keeps Kokoro normalization, vocabulary filtering, fallback scoring,
and pronunciation-view conversion in this repository:

```bash
python benchmarks/benchmark_de_lexicon_sources.py \
  --source gold=path/to/gold.g2lex \
  --source crane=path/to/crane.g2lex \
  --data-root /path/to/crane-test-data --output /tmp/de-quality.json
```

G2Lex owns exact storage, source analysis, and neutral layering metrics; KokoroG2P owns
consumer quality evaluation and phoneme conversion. The first lexicon in
`lexicons=(...)` that contains a word wins. Explicit selections preserve caller order.
If `lexicons` is omitted, manifest default priorities select the compatibility default;
the `load_gold` and `load_silver` flags remain compatibility controls. With an explicit
selection, the named selection takes precedence and legacy flags are ignored.

Maintainers rebuild and validate committed assets with:

```bash
python scripts/build_g2lex_assets.py --all
python scripts/build_g2lex_assets.py --check
python scripts/validate_g2lex_assets.py --all --runtime-parity
```

CMUdict remains Scope A until a pinned, licensed source and a tested Kokoro-compatible
ARPABET conversion are shipped. G2Lex may preserve raw ARPABET exactly, but KokoroG2P
must convert it after lookup, preserve numbered variants deterministically, reject
unknown symbols, and never download it at runtime.
