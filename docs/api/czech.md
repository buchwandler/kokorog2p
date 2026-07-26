# Czech API

Czech G2P provides rule-based phoneme conversion with comprehensive phonological rules.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.cs.CzechG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Examples

```python
from kokorog2p.cs import CzechG2P

g2p = CzechG2P(language="cs-cz")
tokens = g2p("Dobrý den, jak se máte?")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
```

## Phonological Rules

Czech G2P implements the following phonological rules:

- **Palatalization**: d+i → ɟ, t+i → c, n+i → ɲ
- **Long vowels**: á → aː, í → iː, ú/ů → uː, é → eː, ó → oː
- **ř phoneme**: Special raised alveolar trill [r̝]
- **CH digraph**: ch → [x]
- **Final devoicing**: Voiced consonants become voiceless at word end
- **Voicing assimilation**: Consonant clusters assimilate in voicing
