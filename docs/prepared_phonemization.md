# Prepared phonemization

KokoroG2P is the phonological and model-adaptation layer. Its core APIs consume
**prepared, speakable text** plus an explicit language. They preserve that text as the
coordinate space for tokens, annotations, overrides, and results.

```python
from kokorog2p import phonemize_prepared

result = phonemize_prepared("Version two point oh.", language="en-us")
```

The core does not verbalize numbers, abbreviations, units, currencies, dates, times,
URLs, or version labels. Applications that need those semantics must prepare the text
first, for example with the optional Spokenform package, and then call
`phonemize_prepared()`.

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
configured spaCy model for that call.

## Explicit language routing

Language switching is explicit. Use `OverrideSpan` or annotation `language` metadata for
a foreign span. Generic automatic language detection and mixed-language segmentation are
application responsibilities and are not provided by the core package.

## Migration from pre-v0.9

Remove semantic preparation flags such as `input_mode`, `migrated_semantics`, and
`enable_context_detection`. Remove abbreviation registry calls and number/abbreviation
expansion options. Prepare the source text in the owning application or cross-package
pipeline, then pass the prepared result to `phonemize_prepared()` with its explicit
language.
