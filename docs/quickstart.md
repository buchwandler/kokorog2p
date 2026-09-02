# Quick Start

KokoroG2P converts prepared, speakable text to Kokoro phonemes. It does not verbalize
numbers, abbreviations, units, dates, currencies, URLs, or other written semantics.
Prepare those forms in the application layer (for example with Spokenform), then pass
the resulting text to `phonemize_prepared()`.

## Basic usage

```python
from kokorog2p import phonemize_prepared

result = phonemize_prepared("Hello world!", language="en-us")
print(result.phonemes)
```

`phonemize()` is the compatibility spelling for the same prepared-text operation. The
input text is preserved as the coordinate space for tokens and offsets.

## Explicit languages

```python
from kokorog2p import phonemize_prepared

for text, language in [
    ("Hello world!", "en-us"),
    ("Guten Tag", "de"),
    ("Bonjour le monde", "fr"),
    ("안녕하세요", "ko"),
]:
    print(phonemize_prepared(text, language=language).phonemes)
```

Language selection is explicit. For a foreign span, supply an `OverrideSpan` or
annotation language metadata; automatic document-language detection is outside the core
package.

## Prepare semantics outside the core

```python
from spokenform import prepare_for_kokorog2p
from kokorog2p import phonemize_prepared

prepared = prepare_for_kokorog2p("Meet Dr. Smith at 2 kg.", language="en").spoken_text
result = phonemize_prepared(prepared, language="en-us")
```

The optional preparation package is not a KokoroG2P runtime dependency. A minimal core
installation works without it.

## Linguistic annotations

Applications may provide already-computed token metadata without installing a parser:

```python
from kokorog2p import TokenAnnotation, phonemize_prepared

annotations = [TokenAnnotation(0, 6, "record", pos="NOUN", tag="NN")]
result = phonemize_prepared(
    "record this record", language="en-us", annotations=annotations
)
```

Annotation offsets are half-open, ordered, non-overlapping, and relative to the supplied
prepared text. See [the span guide](spans.md) for explicit overrides and offsets.

## G2P instances

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us")
for token in g2p("The quick brown fox"):
    print(token.text, token.phonemes)
```

Use `get_g2p()` for backend-specific controls. Semantic preparation flags and
abbreviation registries are intentionally not part of the v0.9 API.
