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

`crane` is an additional opt-in named lexicon built from the pinned
`crane-local-ai/g2p-lexicons` German Wiktionary TSV. Inspect and select it with:

```python
from kokorog2p import available_lexicons, get_g2p, phonemize

available_lexicons("de")  # ("gold", "crane")
get_g2p("de", lexicons="crane")
phonemize("Haus", language="de", lexicons="crane")
```

The default remains `gold`; an explicit ordered sequence gives precedence to its first
layer, even when casing candidates differ. German lookup tries the exact input,
lowercase, initial-capitalized lowercase, and uppercase forms in that layer order. Crane
retains all source-ordered pronunciations and the runtime selects the first. Its IPA is
normalized centrally for the Kokoro vocabulary (including tie bars, non-syllabic
offglides, syllabic marks, and `ʏ`). The bundled data is CC BY-SA 4.0, attributed to
German Wiktionary contributors, and uses no network access at runtime.
