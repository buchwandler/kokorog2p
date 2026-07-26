# Installation

kokorog2p can be installed with different feature sets depending on your needs.

## Basic Installation

The core package has minimal dependencies:

```bash
pip install kokorog2p
```

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

- spaCy with English model
- US and GB dictionaries (gold/silver tiers)
- Context-dependent pronunciation
- Number and currency expansion

By default, English G2P uses `en_core_web_md` for POS tagging (downloaded on first use
if missing). You can override this with `spacy_model=...`.

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
git clone https://github.com/holgern/kokorog2p.git
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

Download the installer from the [espeak-ng releases page](https://github.com/espeak-ng/espeak-ng/releases).

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

kokorog2p never downloads models during import or inference. Install the
requested model explicitly in the environment that runs the application:

```bash
# Default English model used by kokorog2p
python -m spacy download en_core_web_md

# Optional alternatives
python -m spacy download en_core_web_sm
python -m spacy download en_core_web_lg
```

### Performance Issues

For better performance:

1. Use dictionary-based G2P when possible (English, German, French)
2. Enable caching (enabled by default)
3. Reuse G2P instances instead of creating new ones
4. Consider using espeak-ng fallback only for truly OOV words
