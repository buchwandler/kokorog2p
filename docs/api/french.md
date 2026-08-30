# French API

French G2P provides phoneme conversion using a gold dictionary with espeak-ng fallback.

French semantic preparation runs through the released shared stack:

```text
abbr2words -> French abbreviation/symbol recognition
spokenform -> French semantic written-to-spoken preparation
kokorog2p  -> French G2P, tokenization, and phonemes
```

The span pipeline prepares each homogeneous French run once and rebases the exact source
replacements to document offsets. French typography, tokenization, lexicon lookup,
fallback, and phoneme conversion remain local to kokorog2p. The number helper functions
below are retained for compatibility and are deprecated; new code should call
`spokenform` directly.

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

The public helper functions are deprecated compatibility wrappers around the released
`spokenform` implementation. `FrenchG2P(expand_nums=False)` selects the upstream
no-number-expansion policy, so ordinary written numbers and structured expressions
remain written rather than being silently expanded.

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

## Lexicon storage

French gold data is shipped as a verified lazy G2Lex asset. Built-in corrections retain
precedence over the selected lexicon.
