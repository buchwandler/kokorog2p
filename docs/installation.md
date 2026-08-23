# Installation

kokorog2p can be installed with different feature sets depending on your needs.

## Basic Installation

The core package has minimal dependencies:

```bash
pip install kokorog2p
```

The core install includes runtime dependencies `abbr2words>=0.2.9,<0.3.0` and
`spokenform>=0.3.1,<0.4.0`. `abbr2words` owns abbreviation recognition and
customization, `spokenform` owns reusable written-to-spoken semantic preparation and is
authoritative after accepting a source span, while kokorog2p remains the G2P and phoneme
layer. The declared dependency floor guarantees the released Spokenform 0.3.1 behavior
used by this package.

This gives you:

- Core G2P functionality
- Basic phoneme conversion
- German, Czech support (rule-based)
- Number handling

## With Language Support

### English (with spaCy)

For full English support with POS tagging and advanced tokenization:

```bash
pip install kokorog2p[en]
```

This includes:

- spaCy runtime support (models are installed separately and never downloaded by
  kokorog2p)
- US and GB dictionaries (gold/silver tiers)
- Context-dependent pronunciation
- Number and currency expansion

With `use_spacy=None`, English and French try the highest installed and loadable local
model in `trf > lg > md > sm` order, then fall back to native tokenization when no model
is available. `use_spacy=True`, `spacy_model=...`, and `spacy_model_size="md"` are
strict requests and raise if the requested model is unavailable. No mode downloads
models.

### French

For French support:

```bash
pip install kokorog2p[fr]
```

This includes:

- French gold dictionary
- espeak-ng fallback
- Number and currency handling

### Chinese

For Chinese support:

```bash
pip install kokorog2p[zh]
```

This includes:

- jieba for tokenization
- pypinyin for pinyin conversion
- cn2an for number handling
- Tone sandhi rules

### Japanese

For Japanese support:

```bash
pip install kokorog2p[ja]
```

This includes:

- pyopenjtalk for text analysis
- Cutlet for romanization
- Mora-based phoneme generation

### Mixed-Language Detection

For automatic language detection in mixed-language texts:

```bash
pip install kokorog2p[mixed]
```

This includes:

- lingua-language-detector for high-accuracy detection
- Automatic routing to appropriate G2P engines
- Support for 17+ languages
- Caching for performance

### SSMD and phrasplit integration

The integration adapters are dependency-free. Install the upstream packages only when
your application needs them, and use `overrides_from_ssmd()` plus
`overrides_for_segment()` to keep document-level clean-text offsets aligned with each
sentence. The compatibility test targets are phrasplit 0.3.4 and SSMD 0.8.0; they are
not runtime dependencies of the core package.

## With Backend Support

### espeak-ng Backend

For espeak-ng fallback (recommended for production):

```bash
pip install kokorog2p[espeak]
```

This includes:

- espeak-ng Python bindings
- Fallback for OOV words
- Support for 100+ languages via espeak-ng

### goruut Backend

For goruut backend (experimental):

```bash
pip install kokorog2p[goruut]
```

## Full Installation

To install all features:

```bash
pip install kokorog2p[all]
```

This includes all language packs and backends.

## Development Installation

For development, clone the repository and install in editable mode:

```bash
git clone https://github.com/buchwandler/kokorog2p.git
cd kokorog2p
pip install -e ".[dev]"
```

This includes:

- All language packs and backends
- Development tools (pytest, ruff, mypy)
- Pre-commit hooks
- Documentation building tools

## System Dependencies

### espeak-ng

If using the espeak backend, you'll need espeak-ng installed on your system:

**Ubuntu/Debian:**

```bash
sudo apt-get install espeak-ng
```

**macOS:**

```bash
brew install espeak-ng
```

**Windows:**

Download the installer from the
[espeak-ng releases page](https://github.com/espeak-ng/espeak-ng/releases).

## Verifying Installation

To verify your installation:

```python
import kokorog2p
print(kokorog2p.__version__)

# Test basic functionality
from kokorog2p import phonemize
result = phonemize("Hello world!", language="en-us")
print(result)
```

If you see phoneme output, your installation is successful!

## Troubleshooting

### Import Errors

If you get import errors for optional dependencies:

```python
# Check what's installed
import importlib.util

# Check for spaCy
spacy_available = importlib.util.find_spec("spacy") is not None
print(f"spaCy available: {spacy_available}")

# Check for espeak
espeak_available = importlib.util.find_spec("espeakng_loader") is not None
print(f"espeak-ng available: {espeak_available}")
```

### Missing Language Models

If spaCy models are missing:

kokorog2p never downloads models during import or inference. Install the requested model
explicitly in the environment that runs the application:

```bash
# Install one or more candidates; automatic selection uses the best installed one
python -m spacy download en_core_web_md

# Optional alternatives
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_lg

# Transformer tier (highest quality when installed and loadable)
python -m spacy download en_core_web_trf
```

For French, German, Spanish, Italian, or Portuguese, install the matching
`*_core_news_{trf,lg,md,sm}` package. Automatic errors list every compatible candidate
checked and any load errors. An explicit package or size request is strict and reports
only that requested package; it does not substitute another tier.

### Performance Issues

For better performance:

1. Use dictionary-based G2P when possible (English, German, French)
2. Enable caching (enabled by default)
3. Reuse G2P instances instead of creating new ones
4. Consider using espeak-ng fallback only for truly OOV words
