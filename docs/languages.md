# Language Support

kokorog2p supports multiple languages with varying levels of functionality.

```{eval-rst}
.. list-table:: Language Support Overview
   :header-rows: 1
   :widths: 15 15 20 20 30

   * - Language
     - Code
     - Dictionary
     - Fallback
     - Special Features
   * - English (US)
     - en-us
     - 100k+ entries
     - espeak-ng
     - POS tagging, stress, numbers
   * - English (GB)
     - en-gb
     - 100k+ entries
     - espeak-ng
     - POS tagging, stress, numbers
   * - German
     - de
     - 738k+ entries
     - espeak-ng
     - Phonological rules, numbers
   * - French
     - fr
     - Gold dictionary
     - espeak-ng
     - Numbers, liaison rules
   * - Spanish
     - es
     - Rule-based
     - espeak-ng/goruut
     - Phonological rules, numbers
   * - Italian
     - it
     - Rule-based
     - espeak-ng/goruut
     - Phonological rules, gemination
   * - Portuguese
     - pt
     - Rule-based
     - —
     - Phonological rules, nasalization
   * - Czech
     - cs
     - Rule-based
     - espeak-ng/goruut
     - Phonological rules
   * - Chinese
     - zh
     - —
     - pypinyin
     - Tone sandhi, pinyin
   * - Japanese
     - ja
     - —
     - pyopenjtalk
     - Mora-based, pitch accent
   * - Korean
     - ko
     - —
     - MeCab
     - Phonological rules, liaison
   * - Hebrew
     - he
     - —
     - phonikud
     - Nikud handling, stress
   * - Russian
     - ru-ru
     - RUAccent (optional)
     - espeak-ng
     - Contextual stress, ё restoration, reduction, source-aligned tokens
   * - Kazakh
     - kk
     - —
     - espeak-ng
     - Raw non-English IPA, Kokoro vocabulary validation
   * - Mixed
     - multilingual
     - Auto-detect
     - lingua-py
     - 17+ languages, word-level detection
```

## English (en-us, en-gb)

English G2P uses a two-tier dictionary system with spaCy for POS tagging.

### Features

- **Gold dictionary**: 50k+ high-confidence entries
- **Silver dictionary**: Additional 50k+ entries
- **POS-aware pronunciation**: Different pronunciations based on part of speech
- **Stress assignment**: Primary and secondary stress markers
- **Number handling**: Cardinals, ordinals, currency
- **Contraction support**: Proper handling of "can't", "won't", etc.

### Semantic ownership

English reviewed written-to-spoken preparation runs once per homogeneous language run
through `abbr2words` and `spokenform`, covering shared abbreviations, dates, quantities,
temperatures, currencies, and ordinary number forms. `kokorog2p` retains English
typography, tokenization, alignment, and G2P behavior. Phoneme- sensitive number
categories, including forms whose pronunciation depends on the English G2P context,
remain downstream-owned by the local `NumberConverter` path.

### Usage

```python
from kokorog2p.en import EnglishG2P

# US English
g2p_us = EnglishG2P(
    language="en-us",
    use_espeak_fallback=True,
    use_spacy=True,
    spacy_model="en_core_web_md",  # explicit; unset selects the highest installed model
)

# British English
g2p_gb = EnglishG2P(
    language="en-gb",
    use_espeak_fallback=True,
    use_spacy=True,
    spacy_model="en_core_web_md",  # explicit; unset selects the highest installed model
)

# Optional: automatic selection or an exact model
g2p_auto = EnglishG2P(language="en-us", use_spacy=True)
g2p_sm = EnglishG2P(language="en-us", use_spacy=True, spacy_model="en_core_web_sm")
```

### Examples

```python
from kokorog2p import phonemize

# Context-dependent pronunciation
print(phonemize("I read a book.", language="en-us"))
# → ˈaɪ ɹˈɛd ə bˈʊk.

print(phonemize("I will read tomorrow.", language="en-us"))
# → ˈaɪ wɪl ɹˈid təmˈɑɹO.

# Numbers and currency
print(phonemize("I paid $1,234.56 for it.", language="en-us"))
# → aɪ pˈeɪd wʌn θˈaʊzənd tˈu hˈʌndɹəd...
```

## German (de)

German G2P uses a large dictionary (738k+ entries from Olaph) with rule-based fallback.

### Features

- **Large dictionary**: 738k+ entries with stress markers

- **Phonological rules**:

  - Final obstruent devoicing (Auslautverhärtung)
  - ich-Laut [ç] vs ach-Laut [x] alternation
  - Word-initial sp/st → [ʃp]/[ʃt]
  - Vowel length rules
  - Schwa in unstressed syllables

- **Deterministic normalization**: German cardinals, decimals, thousands groups, years,
  conservative ordinals, dates, times, EUR amounts, temperatures, and numbered units are
  classified before lexical abbreviation expansion.
- **Abbreviations and units**: Flexible `z.B.`, `d.h.`, and `u.a.` forms, common lexical
  abbreviations, and grammatical unit forms such as `1 Std.` → `eine Stunde` and `2 kg`
  → `zwei Kilogramm`.
- **Ambiguity policy**: Bare sentence-final numbers stay cardinals, invalid dates and
  times remain unchanged, and unit symbols only expand when preceded by a number. The
  exact written-to-spoken result, including abbreviation and initialism choices, is
  supplied by the supported Spokenform 0.3.1-compatible profile rather than a second
  kokorog2p rule set.

- **Regional variants**: de-de, de-at, de-ch

German was the first language migrated to the shared semantic-preparation architecture,
followed by French, Spanish, Italian, Portuguese, Czech, and English. These seven
languages use the same per-homogeneous-run `spokenform` path. `abbr2words` remains the
shared source of truth for lexical abbreviation and symbol recognition, while
`spokenform` owns accepted written-to-spoken behavior through its `for_kokorog2p`
profile. The examples in this guide are illustrative; the declared Spokenform 0.3.1
dependency contract is authoritative. Kokorog2p retains only typography and
phoneme-sensitive handling for spans Spokenform leaves protected or unsupported.

### Usage

```python
from kokorog2p.de import GermanG2P

g2p = GermanG2P(
    language="de-de",
    use_espeak_fallback=True,
    strip_stress=True
)
```

### Examples

```python
from kokorog2p import phonemize

# Basic phonemization
print(str(phonemize("Guten Tag", language="de")))
# → ɡuːtn̩ taːk

# Phonological rules
print(str(phonemize("ich", language="de")))      # → ɪç (ich-Laut)
print(str(phonemize("ach", language="de")))      # → ax (ach-Laut)
print(str(phonemize("Tag", language="de")))      # → taːk (final devoicing)

# Numbers
print(str(phonemize("Ich habe 42 Euro.", language="de")))
# → ɪç haːbə t͡svaɪ̯ʊntfɪɐ̯t͡sɪç ɔɪ̯ʁo.
```

## French (fr)

French G2P uses a gold dictionary with espeak-ng fallback.

### Features

- **Gold dictionary**: High-quality French pronunciations
- **Semantic ownership**: `abbr2words` recognizes French abbreviations and symbols;
  `spokenform` prepares dates, times, numbers, ordinals, currencies, quantities, units,
  and temperatures
- **espeak-ng fallback**: For out-of-vocabulary words

French was the second migrated language. kokorog2p retains French typography,
tokenization, lexicon lookup, fallback, and phoneme conversion. The legacy helpers in
`kokorog2p.fr.numbers` remain as deprecated compatibility wrappers.

### Usage

```python
from kokorog2p.fr import FrenchG2P

g2p = FrenchG2P(
    language="fr-fr",
    use_espeak_fallback=True
)
```

### Examples

```python
from kokorog2p import phonemize

print(phonemize("Bonjour le monde", language="fr"))
# → bɔ̃ʒuʁ lə mɔ̃d

print(phonemize("J'ai vingt et un ans.", language="fr"))
# → ʒɛ vɛ̃t e œ̃ ɑ̃.
```

## Czech (cs)

Czech G2P is entirely rule-based with comprehensive phonological rules.

### Features

- **Rule-based phonology**:

  - Palatalization (d+i → ɟ, t+i → c, n+i → ɲ)
  - Long vowels (á → aː, í → iː, etc.)
  - ř phoneme [r̝]
  - ch digraph → [x]
  - Final devoicing
  - Voicing assimilation

- **No dictionary required**: Works with any Czech text

- **Semantic ownership**: `abbr2words` owns Czech abbreviation and canonical
  quantity/currency recognition; `spokenform` owns reusable numbers, dates, quantities,
  temperatures, and currencies; kokorog2p retains Czech typography, tokenization,
  alignment, phonology, lexicon, and fallbacks.

Czech semantic preparation runs once per homogeneous language run. The Czech normalizer
is a downstream typography adapter, so direct `CzechG2P` use and the public pipeline
share the same spokenform preparation. Czech times remain caller-managed.

### Usage

```python
from kokorog2p.cs import CzechG2P

g2p = CzechG2P(language="cs-cz")
```

### Examples

```python
from kokorog2p import phonemize

print(phonemize("Dobrý den", language="cs"))
# → dobriː dɛn

print(phonemize("Praha", language="cs"))
# → praɦa

# Palatalization
print(phonemize("děti", language="cs"))
# → ɟɛcɪ

 # ř phoneme
 print(phonemize("řeka", language="cs"))
 # → r̝ɛka
```

## Spanish (es)

Spanish G2P is rule-based with comprehensive phonological rules for both European and
Latin American dialects.

### Features

- **Rule-based phonology**:

  - 5 pure vowels (a, e, i, o, u)
  - Stress prediction (penultimate for vowel-ending, final for consonant-ending)
  - Palatal sounds: ñ [ɲ], ll [ʎ] or [j]
  - Jota: j/g+e/i [x]
  - Theta: z/c+e/i [θ] (European) or [s] (Latin American)
  - Tap vs trill: r [ɾ] vs rr [r]

- **Dialect support**: es (European), la (Latin American)

- **Number handling**: Cardinals, ordinals, currency

- **Semantic ownership**: `abbr2words` recognizes Spanish abbreviations and symbols;
  `spokenform` prepares written numbers, quantities, temperatures, currencies, and
  reviewed dates; kokorog2p retains typography, tokenization, alignment, and G2P

Spanish semantic preparation is applied once per homogeneous language run. Dialect
selection remains a phoneme-layer concern: `es` provides European theta behavior and
`la` provides Latin-American seseo behavior over the same prepared text.

### Usage

```python
from kokorog2p.es import SpanishG2P

g2p = SpanishG2P(
    language="es",
    dialect="es"  # or "la" for Latin American
)
```

### Examples

```python
from kokorog2p import phonemize

print(phonemize("Hola mundo", language="es"))
# → ola mundo

# Phonological features
print(phonemize("año", language="es"))      # → aɲo
print(phonemize("calle", language="es"))    # → kaʎe or kaje
print(phonemize("perro", language="es"))    # → pero (trilled r)
```

## Italian (it)

Italian G2P uses rule-based phonology with predictable stress and gemination handling.

### Semantic ownership

- `abbr2words` owns Italian lexical abbreviations, units, currency symbols, canonical
  structured IDs, and source-span matching.
- `spokenform` owns reviewed dates, quantities, temperatures, currencies, and ordinary
  written numbers for each homogeneous Italian run.
- kokorog2p retains Italian typography, apostrophe/contraction handling, tokenization,
  spaCy integration, and G2P stress, gemination, phoneme, and vocabulary behavior.

Italian colon times remain caller-managed in this migration. `spokenform` does not
perform language detection, mixed-language segmentation, markup parsing, or phoneme
generation.

### Features

- **Rule-based phonology**:

  - 5 pure vowels (a, e, i, o, u) - no reduction
  - Predictable stress (usually penultimate)
  - Gemination (double consonants) preservation
  - Palatals: gn [ɲ], gli [ʎ]
  - Affricates: z [ʦ/ʣ], c/ci [ʧ], g/gi [ʤ]
  - Context-sensitive c/g pronunciation

- **Stress marking**: Automatic stress detection from accents

- **Number handling**: Cardinals, ordinals

### Usage

```python
from kokorog2p.it import ItalianG2P

g2p = ItalianG2P(
    language="it-it",
    mark_stress=True,
    mark_gemination=True
)
```

### Examples

```python
from kokorog2p import phonemize

print(phonemize("Ciao mondo", language="it"))
# → ʧao mondo

# Gemination
print(phonemize("anno", language="it"))     # → anːo
print(phonemize("fatto", language="it"))    # → fatːo

# Palatals
print(phonemize("gnocchi", language="it"))  # → ɲɔkːi
print(phonemize("figlio", language="it"))   # → fiʎo
```

## Portuguese (pt)

Portuguese semantic preparation is applied once per homogeneous language run. Bare `pt`
and `pt-br` select Brazilian Portuguese wording; `pt-pt` preserves European Portuguese
wording. `abbr2words` owns Portuguese lexical abbreviation and canonical unit/currency
symbol recognition, `spokenform` owns Portuguese written-to-spoken semantics for dates,
numbers, quantities, temperatures, currencies, and reviewed structured forms, and
kokorog2p retains Portuguese typography, tokenization, and G2P. Colon times remain
caller-managed in this migration.

Portuguese G2P supports Brazilian Portuguese with comprehensive phonological rules.

### Features

- **Rule-based phonology**:

  - 7 oral vowels (a, e, ɛ, i, o, ɔ, u)
  - 5 nasal vowels (ã, ẽ, ĩ, õ, ũ)
  - Nasal diphthongs
  - Palatalization: lh [ʎ], nh [ɲ], x/ch [ʃ]
  - Affrication: t+i [ʧ], d+i [ʤ] (Brazilian)
  - Sibilants: s [s/z], x [ʃ], z [z]
  - Liquids: r [ʁ/x/h], rr [ʁ/x], single r [ɾ]

- **Dialect**: Brazilian Portuguese (pt-br) by default; semantic preparation also
  supports European Portuguese wording (pt-pt)

- **Stress marking**: Automatic stress assignment

### Usage

```python
from kokorog2p.pt import PortugueseG2P

g2p = PortugueseG2P(
    language="pt-br",
    mark_stress=True,
    affricate_ti_di=True  # Brazilian feature
)
```

### Examples

```python
from kokorog2p import phonemize

print(phonemize("Olá mundo", language="pt"))
# → ola mundo

# Nasal vowels
print(phonemize("mãe", language="pt"))      # → mãj̃
print(phonemize("pão", language="pt"))      # → pãw̃

# Affrication (Brazilian)
print(phonemize("tia", language="pt"))      # → ʧia
print(phonemize("dia", language="pt"))      # → ʤia
```

## Chinese (zh)

Chinese G2P uses jieba for tokenization and pypinyin for phoneme conversion.

### Features

- **Jieba tokenization**: Chinese word segmentation
- **Pypinyin conversion**: Pinyin to IPA
- **Tone sandhi**: Automatic tone changes
- **cn2an**: Number to Chinese conversion
- **Punctuation mapping**: Chinese to Western punctuation

### Usage

```python
from kokorog2p.zh import ChineseG2P

g2p = ChineseG2P(
    language="zh",
    version="1.1"
)
```

### Examples

```python
from kokorog2p import phonemize

print(phonemize("你好世界", language="zh"))
# → nǐ hǎo shì jiè (with tone markers)
```

## Japanese (ja)

Japanese G2P uses an OpenJTalk-compatible frontend for linguistic analysis, then maps
pronunciation moras and accent metadata into the Kokoro Japanese vocabulary.

### Features

- **OpenJTalk frontend**: Morphological analysis, readings, phrase boundaries, and
  accent data
- **Mora-based mapping**: Japanese pronunciation is converted to Kokoro phoneme symbols
- **Aligned pitch channel**: `JapaneseG2P.phonemize()` returns base phonemes followed by
  an equally long pitch/control channel
- **Optional Cutlet backend**: A legacy romaji backend is available separately

### Usage

```python
from kokorog2p.ja import JapaneseG2P

g2p = JapaneseG2P(
    language="ja",
    backend="pyopenjtalk",
    version="1.0",
)
print(g2p.phonemize("こんにちは"))
```

`backend` selects the linguistic frontend. `version` selects the target Kokoro model
representation and is not a backend selector. The legacy `version="pyopenjtalk"` and
`version="cutlet"` forms are deprecated.

For the legacy backend, install `kokorog2p[ja-cutlet]`. The recommended `ja` extra
contains only the primary OpenJTalk-compatible backend. Full UniDic is an explicit
option and requires `python -m unidic download` after installation.

### Japanese espeak flag

`use_espeak_fallback` is retained for common API compatibility but is not used by the
Japanese backend. It is not a Japanese benchmark or performance configuration.

## Korean (ko)

Korean G2P uses the vendored 5Hyeons `g2pkc` compatibility rules. Morphology is optional
and is used only when a supported Korean analyzer is installed.

### Features

- **g2pkc compatibility baseline**: Korean Standard Pronunciation rules, liaison,
  assimilation, palatalization, tensification, aspiration, and number context
- **Morphology modes**: `auto`, `required`, or `off`
- **Output modes**: `model` (default Kokoro 82M v1.0 alphabet), `ipa`, or positional
  `jamo`
- **Default voice metadata**: `jf_alpha`, the Japanese Kokoro voice requested for Korean
- **Offline behavior**: pure Hangul does not load CMUdict; Latin input requires the NLTK
  CMUdict resource
- **Hanja**: not currently converted; Hanja support is intentionally not claimed
- **Provenance**: see `kokorog2p/ko/README.md` for the frozen source revision and
  checksums

### Usage

```python
from kokorog2p.ko import KoreanG2P

g2p = KoreanG2P(
    language="ko-kr",
    morphology="auto",
    voice="jf_alpha",
    output="model",
 )
```

Use `output="ipa"` for the linguistic IPA-like representation, including positional coda
markers. Use `output="jamo"` to inspect the g2pkc intermediate form. The model output
explicitly maps markers absent from Kokoro 82M v1.0 and rejects other unsupported
symbols.

## Vietnamese (vi-vn)

Vietnamese uses a native pure-Python broad Northern/Hanoi frontend. The aliases `vi`,
`vie`, and `vietnamese` resolve to `vi-vn`. It parses each whitespace-separated syllable
structurally, extracts six named tones, and renders directly with the Kokoro model
profile.

```python
from kokorog2p import phonemize

result = phonemize("Xin chào!", language="vi", return_ids=True)
print(result.phonemes, result.token_ids)
```

No Vietnamese-specific extra or `vig2p` runtime dependency is required. Invalid or
foreign tokens use the existing lazy English fallback by default; pass
`foreign_fallback="none"` or `"espeak"` to `get_g2p`. Semantic number, date, URL, and
currency normalization remains outside this phonology module. See {doc}`api/vietnamese`
and `vi/PROVENANCE` for the model profile, limitations, and clean-room sources.

### Examples

```python
from kokorog2p import phonemize

print(phonemize("안녕하세요", language="ko"))
 # → annjʌŋhasejo

print(phonemize("학교", language="ko"))
 # → hakkjo in the model alphabet

# Explicit linguistic output
from kokorog2p.ko import KoreanG2P
print(KoreanG2P(output="ipa", morphology="off").phonemize("강"))
 # → kaŋ
```

`use_espeak_fallback`, `use_goruut_fallback`, spaCy settings, and dictionary tier flags
are retained for common factory compatibility but do not control Korean pronunciation.

Hebrew G2P uses phonikud for nikud-based phonemization.

### Features

- **phonikud integration**: Hebrew nikud to IPA conversion
- **Nikud handling**: Processes diacritical marks for vowels
- **Stress prediction**: Automatic stress assignment
- **Modern Hebrew**: Optimized for contemporary pronunciation

### Usage

```python
from kokorog2p.he import HebrewG2P

g2p = HebrewG2P(
    language="he-il",
    preserve_punctuation=True,
    preserve_stress=True
)
```

### Examples

```python
from kokorog2p import phonemize

# Requires nikud (diacritical marks)
print(phonemize("שָׁלוֹם", language="he"))
# → ʃalom

print(phonemize("עִבְרִית", language="he"))
# → ivʁit
```

## Mixed-Language Support

kokorog2p can automatically detect and handle texts that mix multiple languages, routing
each word to the appropriate G2P engine.

### Features

- **Automatic detection**: Word-level language detection using lingua-py
- **High accuracy**: >90% accuracy for words with 5+ characters
- **Caching**: Detection results cached for performance
- **Configurable threshold**: Control detection sensitivity
- **Graceful degradation**: Falls back to primary language without lingua-py
- **17+ languages**: Support for major world languages

### Supported Languages

- English (en-us, en-gb)
- German (de)
- French (fr)
- Spanish (es)
- Italian (it)
- Portuguese (pt)
- Japanese (ja)
- Chinese (zh)
- Korean (ko)
- Vietnamese (vi-vn, vi)
- Hebrew (he)
- Czech (cs)
- Dutch (nl)
- Polish (pl)
- Russian (ru)
- Arabic (ar)
- Hindi (hi)
- Turkish (tr)

### Usage

```python
from kokorog2p import phonemize
from kokorog2p.multilang import preprocess_multilang

text = "Das Meeting war great!"
overrides = preprocess_multilang(
    text,
    default_language="de",
    allowed_languages=["de", "en-us"],
)

result = phonemize(text, language="de", overrides=overrides)
```

### Examples

**German with English:**

```python
from kokorog2p import phonemize
from kokorog2p.multilang import preprocess_multilang

text = "Ich gehe zum Meeting. Let's discuss the Roadmap!"
overrides = preprocess_multilang(
    text,
    default_language="de",
    allowed_languages=["de", "en-us"],
)
result = phonemize(text, language="de", overrides=overrides)
print(result.phonemes)
```

**English with German:**

```python
overrides = preprocess_multilang(
    "Hello, mein Freund! This is wunderbar.",
    default_language="en-us",
    allowed_languages=["en-us", "de"],
)
result = phonemize(
    "Hello, mein Freund! This is wunderbar.",
    language="en-us",
    overrides=overrides,
)
print(result.phonemes)
```

**Multiple languages:**

```python
overrides = preprocess_multilang(
    "Bonjour! The Meeting ist wichtig.",
    default_language="fr",
    allowed_languages=["fr", "en-us", "de"],
)
result = phonemize(
    "Bonjour! The Meeting ist wichtig.",
    language="fr",
    overrides=overrides,
)
print(result.phonemes)
```

### Configuration

**Confidence threshold:**

```python
from kokorog2p.multilang import preprocess_multilang

# Conservative (higher confidence required)
overrides = preprocess_multilang(
    "Das Meeting ist wichtig",
    default_language="de",
    allowed_languages=["de", "en-us"],
    confidence_threshold=0.9,  # Default: 0.7
)

# Aggressive (lower confidence required)
overrides = preprocess_multilang(
    "Das Meeting ist wichtig",
    default_language="de",
    allowed_languages=["de", "en-us"],
    confidence_threshold=0.5,
)
```

### How It Works

1. Text is tokenized into words

2. Each word is sent to the language detector

3. Detector returns language + confidence score

4. If confidence ≥ threshold and language is allowed:

   - An `OverrideSpan` is created with `{"lang": "..."}`
   - Short words (\<3 chars) keep the default language

### Performance

- **Memory**: ~100 MB for lingua models (loaded once)
- **Speed**: ~0.1-0.5 ms per word
- **Accuracy**: >90% for words with 5+ characters

### Limitations

- Short words (\<3 characters) use the default language only
- Proper nouns may be misdetected
- Requires `lingua-language-detector` installation
- Detection quality varies by word distinctiveness

### Installation

```bash
pip install kokorog2p[mixed]
```

## Language-Specific Number Handling

### English

```python
from kokorog2p.en.numbers import expand_number

print(expand_number("I have $42.50"))
# → I have forty-two dollars and fifty cents
```

### German

```python
from kokorog2p.de.numbers import expand_number

print(expand_number("Ich habe 42 Euro."))
# → Ich habe zweiundvierzig Euro.
```

### French

```python
from kokorog2p.fr.numbers import expand_number

print(expand_number("J'ai 42 euros."))
# → J'ai quarante-deux euros.
```

## Fallback Languages

Spanish, Italian, and Portuguese have native rule-based implementations. For languages
not explicitly supported, select the eSpeak backend explicitly:

```python
from kokorog2p import get_g2p

# Native Spanish implementation
g2p_es = get_g2p("es-es")

# Native Italian implementation
g2p_it = get_g2p("it-it")

# Native Portuguese implementation
g2p_pt = get_g2p("pt-br")

# Explicit eSpeak backend for another language
g2p_nl = get_g2p("nl", backend="espeak")
```

This provides basic support for 100+ languages via espeak-ng.

## Next Steps

- See {doc}`advanced` for advanced usage patterns

- Check language-specific API docs:

  - {doc}`api/english`
  - {doc}`api/german`
  - {doc}`api/french`
  - {doc}`api/czech`
  - {doc}`api/spanish`
  - {doc}`api/italian`
  - {doc}`api/portuguese`
  - {doc}`api/chinese`
  - {doc}`api/japanese`
  - {doc}`api/korean`
  - {doc}`api/hebrew`
  - {doc}`api/mixed`

## Arabic (MSA)

Arabic support is native and Nabra-compatible for Modern Standard Arabic (MSA). It uses
raw Arabic eSpeak IPA and optionally uses CAMeL MLE diacritization for unvocalized text.
Dialects are not supported by this frontend. See {doc}`api/arabic`.

## Swedish (sv-se)

Swedish uses a native deterministic rule-based grapheme-to-phoneme frontend. It has no
runtime pronunciation lexicon and does not download a model. The external NST-derived
TSV is accepted only by `benchmarks/benchmark_sv_rules.py` for development benchmarking.

Aliases are `sv`, `sv-se`, `swe`, and `swedish`. Swedish number, date, unit,
abbreviation, and spoken semantic normalization remain outside this frontend. See
{doc}`api/swedish`.

## Kazakh (kk)

Kazakh uses eSpeak-NG voice `kk` as its pronunciation engine. The frontend requests raw
non-English IPA, applies only generic Kokoro compatibility transforms, and validates
output against the stock Kokoro 1.0 vocabulary. Install `kokorog2p[kk]`.

The upstream Kazakh voice is currently marked `testing`, so output quality follows the
installed eSpeak-NG release. See {doc}`api/kazakh` and `kk/PROVENANCE`.

## Thai (th-th)

Thai is an optional native frontend using TLTK and PyThaiNLP, with lazy EnglishG2P
pronunciation for Latin runs. Install `kokorog2p[th]`; the aliases `th`, `th-th`, `tha`,
and `thai` share one cached frontend.

Thai output targets `wayu-kokoro-thai-v1`. Its low-tone symbol `˩` uses token ID 7 in an
isolated profile, so it must not be combined with another incompatible custom model
profile in one ID stream. Normalization and recovery diagnostics are source-aware, and
strict mode reports unrecovered lexical material. See {doc}`api/thai` and
`th/PROVENANCE`.
