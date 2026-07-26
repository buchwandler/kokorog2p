# Core API

This module contains the core functionality of kokorog2p.

## Main Functions

```{eval-rst}
.. autofunction:: kokorog2p.phonemize
```

```{eval-rst}
.. autofunction:: kokorog2p.tokenize
```

```{eval-rst}
.. autofunction:: kokorog2p.get_g2p
```

```{eval-rst}
.. autofunction:: kokorog2p.clear_cache
```

```{eval-rst}
.. autofunction:: kokorog2p.reset_abbreviations
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
