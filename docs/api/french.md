# French API

The French frontend phonemizes prepared French text using its dictionary and optional
spaCy/espeak controls. Numbers, currencies, dates, units, and abbreviations are not
expanded by KokoroG2P.

```python
from kokorog2p.fr import FrenchG2P

g2p = FrenchG2P(language="fr", use_spacy=False)
print(g2p.phonemize("Bonjour le monde"))
```

Semantic preparation and language segmentation belong to the caller. The frontend keeps
prepared source text and offsets stable.
