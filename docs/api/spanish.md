# Spanish API

The Spanish frontend provides intrinsic Spanish phonological normalization and G2P for
prepared text. Semantic expansion of written numbers, quantities, dates, units,
currencies, and abbreviations belongs to the calling application.

```python
from kokorog2p.es import SpanishG2P

g2p = SpanishG2P(language="es")
print(g2p.phonemize("Hola mundo"))
```

Select the supported dialect explicitly when needed. The frontend does not detect or
segment document languages automatically.
