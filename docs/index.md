# Welcome to kokorog2p's documentation!

**kokorog2p** is a unified G2P (Grapheme-to-Phoneme) library for Kokoro TTS, providing
high-quality text-to-phoneme conversion for multiple languages.

```{image} https://img.shields.io/pypi/v/kokorog2p.svg
:alt: PyPI version
:target: https://pypi.org/project/kokorog2p/
```

```{image} https://img.shields.io/pypi/pyversions/kokorog2p.svg
:alt: Python versions
:target: https://pypi.org/project/kokorog2p/
```

## Features

- **Multi-language support**: English (US/GB), German, French, Czech, Spanish, Italian,
  Portuguese, Chinese, Japanese, Korean, Hebrew, Vietnamese
- **Native Vietnamese**: Pure-Python Northern/Hanoi profile with NFC/NFD support and six
  named tones
- **Mixed-language detection**: Automatic detection and handling of texts mixing
  multiple languages
- **Dictionary-based lookup** with large gold/silver tier lexicons for select languages
- **Rule-based G2P** for Romance and Slavic languages with comprehensive phonological
  rules
- **espeak-ng integration** as a fallback for out-of-vocabulary words
- **Automatic IPA to Kokoro phoneme conversion**
- **Number and currency handling** across all languages
- **Stress assignment** based on linguistic rules
- **High performance** with caching and optimized lookup

## Quick Start

```python
from kokorog2p import phonemize

# English
phonemes = phonemize("Hello world!", language="en-us").phonemes
print(phonemes)  # hˈɛlO wˈɜɹld!

# German
phonemes = phonemize("Guten Tag", language="de").phonemes
print(phonemes)  # ɡuːtn̩ taːk

# French
phonemes = phonemize("Bonjour", language="fr").phonemes
print(phonemes)  # bɔ̃ʒuʁ
```

## Installation

```bash
# Core package
pip install kokorog2p

# With English support (includes spaCy)
pip install kokorog2p[en]

# With espeak-ng backend
pip install kokorog2p[espeak]

# Full installation (all languages and backends)
pip install kokorog2p[all]
```

```{toctree}
:caption: User Guide
:maxdepth: 2

installation
quickstart
languages
advanced
abbreviation_customization
spans
phonemes
```

```{toctree}
:caption: API Reference
:maxdepth: 2

api/core
api/english
api/german
api/french
api/czech
api/spanish
api/italian
api/portuguese
api/chinese
api/japanese
api/korean
api/vietnamese
api/hebrew
api/mixed
api/arabic
api/backends
api/utils
```

```{toctree}
:caption: Development
:maxdepth: 1

contributing
changelog
```

# Indices and tables

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
