# German API

German G2P provides phoneme conversion using a large 738k+ entry dictionary with
rule-based fallback.

German normalization is deterministic and runs before tokenization. In the public
default span pipeline, structured replacements are matched against the original
source offsets and then merged into semantic token spans before token-local expansion.
This keeps numeric context intact for grouped numbers (`1.000`), decimals (`3,14`),
EUR amounts, dates, times, temperatures, ordinals, and numbered units with
singular/plural agreement, including when the backend has no language-owned
normalizer. Unit symbols are context bound: `2 kg` becomes `zwei Kilogramm`, while a
standalone `kg` is preserved. Dotted numeric aliases such as `1 ltr.` and `45 Min.`
are consumed as part of the semantic span, so their periods are not treated as
independent sentence punctuation. `Min.` is intentionally numeric-only: standalone
`Min. Beispiel` remains unchanged, while `1 Min.` becomes `eine Minute`.
Invalid dates/times and ambiguous punctuation are left unchanged. Flexible `z.B.`,
`d.h.`, and `u.a.` spellings are supported; `ca.` is normalized to `zirka`, `etc.` to
`ezetera`, and `GmbH`/`AG` to German letter-name spellings.

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
