# Documentation for kokorog2p

This directory contains the Sphinx documentation for kokorog2p.

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
python -m pip install -e ".[docs]"
```

### Build HTML Documentation

From the `docs/` directory:

```bash
python make.py html
```

Or using sphinx-build directly:

```bash
sphinx-build -b html . _build/html
```

### View Documentation

Open `_build/html/index.html` in your web browser:

```bash
# On macOS
open _build/html/index.html

# On Linux
xdg-open _build/html/index.html

# On Windows
start _build/html/index.html
```

## Documentation Structure

```
docs/
├── index.md                  # Main documentation index
├── installation.md           # Installation guide
├── quickstart.md            # Quick start guide
├── languages.md             # Language support overview
├── advanced.md              # Advanced usage
├── phonemes.md              # Phoneme inventory reference
├── contributing.md          # Contributing guide
├── changelog.md             # Changelog
├── api/                     # API Reference
│   ├── core.md             # Core API
│   ├── english.md          # English G2P API
│   ├── german.md           # German G2P API
│   ├── french.md           # French G2P API
│   ├── czech.md            # Czech G2P API
│   ├── spanish.md          # Spanish G2P API
│   ├── italian.md          # Italian G2P API
│   ├── portuguese.md       # Portuguese G2P API
│   ├── chinese.md          # Chinese G2P API
│   ├── japanese.md         # Japanese G2P API
│   ├── korean.md           # Korean G2P API
│   ├── hebrew.md           # Hebrew G2P API
│   ├── backends.md         # Backend APIs
│   └── utils.md            # Utility APIs
├── conf.py                  # Sphinx configuration
├── make.py                  # Build script
└── requirements.txt         # Documentation dependencies
```

## Documentation Pages

### User Guide

1. **Installation** (`installation.md`)

   - Installation methods
   - Optional dependencies
   - System requirements
   - Troubleshooting

2. **Quick Start** (`quickstart.md`)

   - Basic usage
   - Language-specific examples
   - Token inspection
   - Number handling

3. **Languages** (`languages.md`)

   - Supported languages
   - Language-specific features
   - Examples for each language

4. **Advanced Usage** (`advanced.md`)

   - Custom G2P configuration
   - Token inspection
   - Dictionary lookup
   - Phoneme utilities
   - Caching and performance

5. **Phoneme Inventory** (`phonemes.md`)
   - Complete phoneme reference
   - US vs GB English differences
   - German, French, Czech phonemes
   - Conversion utilities

### API Reference

- **Core API** - Main functions and classes
- **English API** - English G2P detailed reference
- **German API** - German G2P detailed reference
- **French API** - French G2P detailed reference
- **Czech API** - Czech G2P detailed reference
- **Spanish API** - Spanish G2P detailed reference
- **Italian API** - Italian G2P detailed reference
- **Portuguese API** - Portuguese G2P detailed reference
- **Chinese API** - Chinese G2P detailed reference
- **Japanese API** - Japanese G2P detailed reference
- **Korean API** - Korean G2P detailed reference
- **Hebrew API** - Hebrew G2P detailed reference
- **Backends API** - espeak-ng and goruut backends
- **Utilities API** - Helper functions and utilities

### Development

- **Contributing** (`contributing.md`)

  - Development setup
  - Running tests
  - Code quality
  - Adding new languages
  - Submitting changes

- **Changelog** (`changelog.md`)
  - Version history
  - Release notes

## Known Issues

### HTML Encoding

Apostrophes in code examples are HTML-encoded as `&#39;` which is correct behavior for
HTML. They will display correctly in browsers as regular apostrophes (').

### Autodoc Warnings

Some autodoc warnings may appear for:

- Duplicate object descriptions (intentional for showing both class and method docs)
- Missing attributes (some classes don't export all internal classes)

These warnings don't affect the generated documentation quality.

## Updating Documentation

When adding new features:

1. Update relevant `.md` files
2. Add docstrings to new code
3. Rebuild documentation: `python make.py html`
4. Check for warnings: Review build output
5. Verify HTML output looks correct

## Publishing Documentation

Documentation can be published to:

- ReadTheDocs (automatic from GitHub)
- GitHub Pages (via CI/CD)
- Package documentation on PyPI

Configure `.readthedocs.yaml` for ReadTheDocs deployment.
