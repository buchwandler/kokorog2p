# Documentation for kokorog2p

This directory contains the Sphinx documentation for kokorog2p.

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -r requirements.txt
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
├── index.rst                 # Main documentation index
├── installation.rst          # Installation guide
├── quickstart.rst           # Quick start guide
├── languages.rst            # Language support overview
├── advanced.rst             # Advanced usage
├── phonemes.rst             # Phoneme inventory reference
├── contributing.rst         # Contributing guide
├── changelog.rst            # Changelog
├── api/                     # API Reference
│   ├── core.rst            # Core API
│   ├── english.rst         # English G2P API
│   ├── german.rst          # German G2P API
│   ├── french.rst          # French G2P API
│   ├── czech.rst           # Czech G2P API
│   ├── spanish.rst         # Spanish G2P API
│   ├── italian.rst         # Italian G2P API
│   ├── portuguese.rst      # Portuguese G2P API
│   ├── chinese.rst         # Chinese G2P API
│   ├── japanese.rst        # Japanese G2P API
│   ├── korean.rst          # Korean G2P API
│   ├── hebrew.rst          # Hebrew G2P API
│   ├── backends.rst        # Backend APIs
│   └── utils.rst           # Utility APIs
├── conf.py                  # Sphinx configuration
├── make.py                  # Build script
└── requirements.txt         # Documentation dependencies
```

## Documentation Pages

### User Guide

1. **Installation** (`installation.rst`)

   - Installation methods
   - Optional dependencies
   - System requirements
   - Troubleshooting

2. **Quick Start** (`quickstart.rst`)

   - Basic usage
   - Language-specific examples
   - Token inspection
   - Number handling

3. **Languages** (`languages.rst`)

   - Supported languages
   - Language-specific features
   - Examples for each language

4. **Advanced Usage** (`advanced.rst`)

   - Custom G2P configuration
   - Token inspection
   - Dictionary lookup
   - Phoneme utilities
   - Caching and performance

5. **Phoneme Inventory** (`phonemes.rst`)
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

- **Contributing** (`contributing.rst`)

  - Development setup
  - Running tests
  - Code quality
  - Adding new languages
  - Submitting changes

- **Changelog** (`changelog.rst`)
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

1. Update relevant `.rst` files
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
