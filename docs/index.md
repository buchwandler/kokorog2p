# kokorog2p documentation

**kokorog2p** is a multilingual grapheme-to-phoneme and Kokoro model adaptation layer.
The core accepts prepared, speakable text and an explicit language.

## Responsibility boundary

KokoroG2P owns tokenization, phonological normalization, language routing requested by
the caller, annotations, overrides, and phoneme/model output. It does not verbalize
numbers, abbreviations, units, currencies, dates, URLs, or other written semantics.
Applications may prepare those forms with an external tool such as Spokenform before
calling `phonemize_prepared()`.

## Quick start

```python
from kokorog2p import phonemize_prepared

result = phonemize_prepared("Hello world!", language="en-us")
print(result.phonemes)
```

See [Quick Start](quickstart.md), [prepared phonemization](prepared_phonemization.md),
and the [span guide](spans.md) for details.

```{toctree}
:maxdepth: 2
:caption: API Reference

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
api/russian
api/hebrew
api/thai
api/kazakh
api/arabic
api/backends
api/utils
```

```{toctree}
:maxdepth: 2
:caption: Guides

quickstart
prepared_phonemization
languages
spans
advanced
installation
```
