# Core API

This module contains the core functionality of kokorog2p.

## Main Functions

```{eval-rst}
.. autofunction:: kokorog2p.phonemize
```

## Structured stress overrides

`OverrideSpan` supports explicit phoneme stress changes through the `stress` attribute.
Values are strings and must be one of `"-2"`, `"-1"`, `"+1"`, or `"+2"`. The stress
change is applied after language resolution and pronunciation or `ph` override
resolution.

```python
from kokorog2p import OverrideSpan, phonemize

result = phonemize(
    "zwei Minuten",
    language="de",
    overrides=[OverrideSpan(0, 4, {"stress": "+2"})],
)
```

The values mean:

- `-2`: remove stress markers.
- `-1`: lower stress by one level.
- `+1`: raise stress by one level.
- `+2`: promote or force primary stress.

A span covering multiple lexical tokens applies independently to each spoken token. This
changes phoneme stress markers (`ˌ` and `ˈ`), not volume, pitch, duration, or SSML
emphasis. Markdown, Misaki, Kokoro markup, and other prosody syntax are not supported.

## Prepared input

Use `phonemize_prepared` when the caller has already converted written text to spoken
text. It retains kokorog2p tokenization, G2P, model punctuation handling, overrides,
phoneme construction, and token IDs, but does not run written-to-spoken semantic
expansion again.

All canonical public entry points require the language to be supplied explicitly.
`phonemize`, `phonemize_prepared`, and `tokenize` require `language=...`; the
convenience wrappers `phonemes` and `phoneme_ids` follow the same rule.

```{eval-rst}
.. autofunction:: kokorog2p.phonemize_prepared
```

The supplied string is the coordinate authority: `clean_text` and token/override offsets
refer to the prepared text. Do not pass arbitrary written text when number, date, unit,
currency, or abbreviation expansion is expected.

```{eval-rst}
.. autofunction:: kokorog2p.tokenize
```

```{eval-rst}
.. autofunction:: kokorog2p.get_g2p
```

```{eval-rst}
.. autofunction:: kokorog2p.clear_cache
```

## Pipeline integration adapters

These adapters accept SSMD- and phrasplit-shaped objects structurally, without making
either package a runtime dependency:

```{eval-rst}
.. autofunction:: kokorog2p.coerce_override_spans
```

```{eval-rst}
.. autofunction:: kokorog2p.overrides_from_ssmd
```

```{eval-rst}
.. autofunction:: kokorog2p.overrides_for_segment
```

```{eval-rst}
.. autofunction:: kokorog2p.phonemize_segments
```

## Base Classes

### G2PBase

```{eval-rst}
.. autoclass:: kokorog2p.G2PBase
   :members:
   :undoc-members:
   :show-inheritance:
```

### GToken

```{eval-rst}
.. autoclass:: kokorog2p.GToken
   :members:
   :undoc-members:
   :show-inheritance:

   .. attribute:: text

      The original text of this token.

   .. attribute:: phonemes

      The IPA phoneme string for this token.

   .. attribute:: tag

      Part-of-speech tag (if available).

   .. attribute:: whitespace

      Whitespace following this token.
```

## Phoneme Utilities

### Vocabulary

```{eval-rst}
.. autofunction:: kokorog2p.get_vocab
```

```{eval-rst}
.. autofunction:: kokorog2p.validate_phonemes
```

```{eval-rst}
.. autodata:: kokorog2p.US_VOCAB
   :annotation:
```

```{eval-rst}
.. autodata:: kokorog2p.GB_VOCAB
   :annotation:
```

```{eval-rst}
.. autodata:: kokorog2p.VOWELS
   :annotation:
```

```{eval-rst}
.. autodata:: kokorog2p.CONSONANTS
   :annotation:
```

### Conversion

```{eval-rst}
.. autofunction:: kokorog2p.from_espeak
```

```{eval-rst}
.. autofunction:: kokorog2p.from_goruut
```

```{eval-rst}
.. autofunction:: kokorog2p.to_espeak
```

## Kokoro Vocabulary

### Encoding/Decoding

```{eval-rst}
.. autofunction:: kokorog2p.encode
```

```{eval-rst}
.. autofunction:: kokorog2p.decode
```

```{eval-rst}
.. autofunction:: kokorog2p.phonemes_to_ids
```

```{eval-rst}
.. autofunction:: kokorog2p.ids_to_phonemes
```

### Validation

```{eval-rst}
.. autofunction:: kokorog2p.validate_for_kokoro
```

```{eval-rst}
.. autofunction:: kokorog2p.filter_for_kokoro
```

### Configuration

```{eval-rst}
.. autofunction:: kokorog2p.get_kokoro_vocab
```

```{eval-rst}
.. autofunction:: kokorog2p.get_kokoro_config
```

```{eval-rst}
.. autodata:: kokorog2p.N_TOKENS
   :annotation:
```

```{eval-rst}
.. autodata:: kokorog2p.PAD_IDX
   :annotation:
```

## Punctuation

```{eval-rst}
.. autoclass:: kokorog2p.Punctuation
   :members:
   :undoc-members:
```

```{eval-rst}
.. autofunction:: kokorog2p.normalize_punctuation
```

```{eval-rst}
.. autofunction:: kokorog2p.filter_punctuation
```

```{eval-rst}
.. autofunction:: kokorog2p.is_kokoro_punctuation
```

```{eval-rst}
.. autodata:: kokorog2p.KOKORO_PUNCTUATION
   :annotation:
```

## Word Mismatch Detection

```{eval-rst}
.. autoclass:: kokorog2p.MismatchMode
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: kokorog2p.MismatchInfo
   :members:
   :undoc-members:
```

```{eval-rst}
.. autoclass:: kokorog2p.MismatchStats
   :members:
   :undoc-members:
```

```{eval-rst}
.. autofunction:: kokorog2p.detect_mismatches
```

```{eval-rst}
.. autofunction:: kokorog2p.check_word_alignment
```

```{eval-rst}
.. autofunction:: kokorog2p.count_words
```
