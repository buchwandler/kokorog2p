# German API

The German frontend provides dictionary and phonological G2P for prepared German text.
Written numbers, units, currencies, dates, and abbreviations must be prepared by the
caller; this package does not expand them.

```python
from kokorog2p.de import GermanG2P

g2p = GermanG2P(language="de")
print(g2p.phonemize("Guten Tag"))
```

Use `get_g2p("de")` for factory construction. Intrinsic German phonological rules and
optional backend selection remain available.
