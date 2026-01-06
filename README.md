# kokorog2p

A unified multi-language G2P (Grapheme-to-Phoneme) library for Kokoro TTS.

kokorog2p converts text to phonemes optimized for the Kokoro text-to-speech system. It
provides:

- **Multi-language support**: English (US/GB), German, French, Italian, Spanish,
  Portuguese (Brazilian), Czech, Chinese, Japanese, Korean, Hebrew
- **Mixed-language detection**: Automatically detect and handle mixed-language texts
  (e.g., German text with English words)
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

# With mixed-language detection support
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

# Automatic punctuation normalization
g2p = get_g2p("en-us")
tokens = g2p("Wait... really?")       # ... → … (ellipsis)
tokens = g2p("Wait - what?")          # - → — (em dash when spaced)
tokens = g2p("don't worry")           # All apostrophe variants → '
tokens = g2p("well-known topic")      # Hyphens in compounds preserved

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

## Mixed-Language Support

kokorog2p can automatically detect and handle mixed-language texts using the
high-accuracy lingua-py library. This is especially useful for technical documents,
social media, or any text that contains words from multiple languages.

### Installation

```bash
# Install with mixed-language support
pip install kokorog2p[mixed]

# Or install lingua-py directly
pip install lingua-language-detector
```

### Basic Usage

```python
from kokorog2p import get_g2p

# German text with English words
g2p = get_g2p(
    language="de",  # Primary language
    multilingual_mode=True,
    allowed_languages=["de", "en-us"]  # Languages to detect
)

text = "Ich gehe zum Meeting. Let's discuss the Roadmap!"
result = g2p.phonemize(text)
# Automatically detects:
# - "Ich gehe zum Meeting" → German G2P
# - "Let's discuss the Roadmap" → English G2P
```

### Advanced Configuration

```python
from kokorog2p import get_g2p

# Multiple languages with custom confidence threshold
g2p = get_g2p(
    language="en-us",  # Primary/fallback language
    multilingual_mode=True,
    allowed_languages=["en-us", "de", "fr", "es"],
    language_confidence_threshold=0.6  # Lower = more aggressive detection
)

# Access detected language for each word
tokens = g2p("Hello! Bonjour! Hola!")
for token in tokens:
    if token.is_word:
        detected_lang = token.get("detected_language")
        print(f"{token.text}: {detected_lang} → {token.phonemes}")
```

### Direct API

```python
from kokorog2p.mixed_language_g2p import MixedLanguageG2P

g2p = MixedLanguageG2P(
    primary_language="de",
    allowed_languages=["de", "en-us"],
    confidence_threshold=0.7,  # Default: 0.7 (recommended)
    enable_detection=True
)

# Check cache size
print(f"Cached words: {g2p.get_cache_size()}")

# Clear cache if needed (for very large texts)
g2p.clear_detection_cache()
```

### How It Works

1. **Tokenization**: Text is split into words using the primary language's tokenizer
2. **Detection**: Each word is analyzed by lingua-py for language identification
3. **Routing**: Words are sent to the appropriate language-specific G2P engine
4. **Caching**: Detection results are cached for performance
5. **Fallback**: Words below confidence threshold use the primary language

### Performance

- **Memory**: Adds ~100 MB (lingua models) + memory for each enabled language
- **Speed**: ~0.1-0.5 ms per word detection (very fast, Rust-based)
- **Accuracy**: >90% for words with 5+ characters
- **Cache**: Unlimited size by default (clear manually if needed)

### Configuration Tips

**Confidence Threshold:**

- `0.5`: More aggressive, may mis-detect ambiguous words
- `0.7`: **Recommended** - balanced precision and recall
- `0.9`: Conservative, most words fall back to primary language

**Allowed Languages:**

- Only specify languages that actually appear in your text
- Fewer languages = faster detection and better accuracy
- Must be explicitly defined by the user (no defaults)

### Limitations

- Very short words (<3 chars) always use primary language
- Ambiguous words (e.g., "Supermarket" in German/English) use primary language
- Script-based detection (Latin, Cyrillic, CJK) happens before linguistic analysis
- Detected language must be in `allowed_languages` list

### Example: Technical Documentation

```python
from kokorog2p import get_g2p

# German technical manual with English terms
g2p = get_g2p(
    language="de",
    multilingual_mode=True,
    allowed_languages=["de", "en-us"]
)

text = """
Das System verwendet Machine Learning für die Performance-Optimierung.
Der Workflow ist sehr efficient durch das Caching.
"""

tokens = g2p(text)
for token in tokens:
    if token.is_word:
        lang = token.get("detected_language")
        print(f"{token.text:20} {lang:6} {token.phonemes}")
```

Output:

```
Das                  de     das
System               de     zʏsteːm
verwendet            de     fɛɐ̯vɛndət
Machine              en-us  məʃˈiːn
Learning             en-us  lˈɜːnɪŋ
...
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
