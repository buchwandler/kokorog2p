# Prepared phonemization

KokoroG2P is a grapheme-to-phoneme and Kokoro model adaptation layer. Its core API
consumes already speakable text, an explicit language, and optional linguistic
annotations.

```python
from kokorog2p import phonemize_prepared

result = phonemize_prepared("Version two point oh.", language="en-us")
```

Numbers, abbreviations, units, currencies, dates, times, URLs, and version labels are
not verbalized by KokoroG2P. Applications that need those semantics must prepare the
text first, for example with Spokenform, and then call `phonemize_prepared()`.

## Linguistic annotations

Applications can inject analysis results without making KokoroG2P import the analysis
package. Objects need `start`, `end`, and may provide `text`, `pos`, `tag`, `lemma`, and
`language`.

```python
from kokorog2p import TokenAnnotation, phonemize_prepared

annotations = [
    TokenAnnotation(0, 6, "record", pos="NOUN", tag="NN", lemma="record")
]
result = phonemize_prepared(
    "record this record", language="en-us", annotations=annotations
)
```

Offsets are half-open source offsets. They must be ordered, non-overlapping, within the
supplied text, and an annotation's optional text must match its source slice. When
annotations are supplied, the pipeline uses them for POS metadata and does not run the
configured spaCy model for that call. Without annotations, standalone G2P instances may
still use explicitly enabled spaCy models.

Language switching is explicit. Use `OverrideSpan` or annotation `language` metadata for
a foreign span. Generic automatic document-language detection is not part of the core
pipeline. The legacy `preprocess_multilang()` helper is retained only as a deprecated
opt-in compatibility helper.
