# Italian API

Italian G2P provides rule-based phoneme conversion for Italian, designed for Kokoro TTS
models.

## Semantic preparation

Italian uses the shared per-language-run semantic-preparation path. `abbr2words`
recognizes Italian abbreviations, units, and currency symbols; `spokenform` verbalizes
reviewed dates, quantities, temperatures, currencies, and ordinary numbers. kokorog2p
keeps Italian typography, tokenization, contractions, stress, gemination, and phoneme
generation downstream. Italian colon times remain caller-managed in this migration.

This boundary does not make `spokenform` responsible for language detection,
mixed-language segmentation, markup parsing, or phoneme generation.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.it.ItalianG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Examples

```python
from kokorog2p.it import ItalianG2P

g2p = ItalianG2P(language="it-it")
tokens = g2p("Ciao mondo!")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
```

## Phonology Features

Italian phonology includes:

- 5 pure vowels (a, e, i, o, u) - always pronounced clearly
- No vowel reduction (unlike English)
- Predictable stress (usually penultimate syllable)
- Gemination (double consonants) is phonemically distinctive
- Palatals: gn [ɲ], gli [ʎ]
- Affricates: z [ʦ/ʣ], c/ci [ʧ], g/gi [ʤ]
- No diphthongs in standard Italian (consecutive vowels are separate syllables)
