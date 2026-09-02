# Italian API

The Italian frontend provides intrinsic Italian phonology for prepared text. Written
semantic expansion and generic language segmentation are outside this module.

```python
from kokorog2p.it import ItalianG2P

g2p = ItalianG2P(language="it")
print(g2p.phonemize("Ciao mondo"))
```

Pass prepared text and select the language explicitly through the public API.
