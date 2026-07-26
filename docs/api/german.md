# German API

German G2P provides phoneme conversion using a large 738k+ entry dictionary with rule-based fallback.

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
