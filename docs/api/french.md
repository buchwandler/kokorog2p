# French API

French G2P provides phoneme conversion using a gold dictionary with espeak-ng fallback.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.fr.FrenchG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Lexicon

```{eval-rst}
.. autoclass:: kokorog2p.fr.FrenchLexicon
   :members:
   :undoc-members:
   :show-inheritance:
```

## Number Conversion

### Helper Functions

```{eval-rst}
.. autofunction:: kokorog2p.fr.numbers.number_to_french
```

```{eval-rst}
.. autofunction:: kokorog2p.fr.numbers.expand_numbers
```

```{eval-rst}
.. autofunction:: kokorog2p.fr.numbers.expand_time
```

```{eval-rst}
.. autofunction:: kokorog2p.fr.numbers.expand_currency
```

```{eval-rst}
.. autofunction:: kokorog2p.fr.numbers.expand_ordinal
```

```{eval-rst}
.. autofunction:: kokorog2p.fr.numbers.is_available
```

## Examples

```python
from kokorog2p.fr import FrenchG2P

g2p = FrenchG2P(language="fr-fr")
tokens = g2p("Bonjour le monde!")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
```
