# German API

German G2P provides phoneme conversion using a large 738k+ entry dictionary with
rule-based fallback.

German semantic normalization is provided by `spokenform` and runs once per homogeneous
language run before token-local G2P processing. In the public default span pipeline,
spokenform source replacements are rebased to original document offsets and merged into
semantic token spans before token-local expansion. This keeps numeric context intact for
grouped numbers (`1.000`), decimals (`3,14`), EUR amounts, dates, times, temperatures,
ordinals, and numbered units with singular/plural agreement, including when the backend
has no language-owned normalizer. Unit symbols are context bound: `2 kg` becomes
`zwei Kilogramm`, while a standalone `kg` is preserved. Dotted numeric aliases such as
`1 ltr.` and `45 Min.` are consumed as part of the semantic span, so their periods are
not treated as independent sentence punctuation. `Min.` is intentionally numeric-only:
standalone `Min. Beispiel` remains unchanged, while `1 Min.` becomes `eine Minute`.
Invalid dates/times and ambiguous punctuation are left unchanged. Flexible `z.B.`,
`d.h.`, and `u.a.` spellings are supported through the Spokenform 0.3.1-compatible and
abbr2words profiles. Accepted semantic replacements are not rewritten by kokorog2p; only
German G2P typography remains local.

`GermanNormalizer` remains available as a compatibility facade for direct callers. Its
semantic result is backed by spokenform, while G2P-specific German typography remains
local. Abbreviation customization continues to use the shared `abbr2words` registry.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.de.GermanG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Lexicon

```{eval-rst}
.. autoclass:: kokorog2p.de.GermanLexicon
   :members:
   :undoc-members:
   :show-inheritance:
```

## Number Conversion

```{eval-rst}
.. autoclass:: kokorog2p.de.numbers.GermanNumberConverter
   :members:
   :undoc-members:
```

```{eval-rst}
.. autofunction:: kokorog2p.de.numbers.expand_number
```

```{eval-rst}
.. autofunction:: kokorog2p.de.numbers.number_to_german
```

```{eval-rst}
.. autofunction:: kokorog2p.de.numbers.ordinal_to_german
```

## Examples

```python
from kokorog2p.de import GermanG2P

g2p = GermanG2P(language="de-de")
tokens = g2p("Guten Tag, wie geht es Ihnen?")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
```

## Lexicon storage

German gold data is stored in the canonical source tree and shipped as a verified lazy
G2Lex asset. `get_g2p("de", lexicons="gold")` selects it explicitly.

The additional `crane`, `espeak`, and `olaph` dictionaries are opt-in named lexicons:

```python
from kokorog2p import available_lexicons, get_g2p, phonemize

available_lexicons("de")  # ("gold", "crane", "espeak", "olaph")
get_g2p("de")  # gold only
get_g2p("de", lexicons="crane")
get_g2p("de", lexicons="espeak")
get_g2p("de", lexicons="olaph")
phonemize("Haus", language="de", lexicons=("gold", "olaph"))
```

Explicit tuple order defines collision precedence. German casing candidates are searched
inside each layer in that order. The Crane source is preserved byte-for-byte for
provenance, but its packaged runtime derivative uses NFC-lowercase keys. Case-colliding
Crane pronunciations may be enriched with POS selectors using the pinned LexHint German
build artifact; `DEFAULT` keeps lookups correct when no POS tag is available. Raw TSV
logical parity is therefore not expected for Crane. `espeak` is a bundled static
dictionary, not the optional `use_espeak_fallback=True` backend. All lookup is offline.
German source IPA is normalized centrally for the Kokoro vocabulary; unsupported values
fail closed and can fall through to configured fallback. The CSTR eSpeak-derived source
has conservative CC BY-SA 3.0 open-dict-data/Wiktionary provenance. OLaPh is MIT
licensed.
