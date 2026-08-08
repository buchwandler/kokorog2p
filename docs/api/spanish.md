# Spanish API

Spanish G2P provides rule-based phoneme conversion for Spanish, designed for Kokoro TTS
models.

## Text preparation ownership

`abbr2words` owns Spanish abbreviation and symbol recognition, `spokenform` owns
semantic written-to-spoken preparation for numbers, quantities, temperatures,
currencies, and reviewed dates, and kokorog2p owns downstream typography, tokenization,
overrides, alignment, and G2P. European (`dialect="es"`) and Latin-American
(`dialect="la"`) phoneme behavior remains local to `SpanishG2P`.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.es.SpanishG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Examples

```python
from kokorog2p.es import SpanishG2P

g2p = SpanishG2P(language="es-es")
tokens = g2p("¡Hola mundo!")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
```

## Phonology Features

Spanish phonology includes:

- 5 pure vowels (a, e, i, o, u) - always pronounced clearly
- No vowel reduction (unlike English)
- Predictable stress (penultimate for vowel-ending words, final for consonant-ending)
- Palatal sounds: ñ [ɲ], ll [ʎ] (or [j] in most dialects), ch [ʧ]
- Jota: j/g+e/i [x]
- Theta: z/c+e/i [θ] in European Spanish (or [s] in Latin America)
- Tap vs trill: r [ɾ] vs rr/initial r [r]
- No consonant clusters simplification
