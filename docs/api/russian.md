# Russian API

The Russian frontend provides stress, orthographic, and eSpeak-based phonological
adaptation for prepared Russian text. Written semantic expansion and language detection
are outside the frontend.

```python
from kokorog2p.ru import RussianG2P

g2p = RussianG2P()
print(g2p.phonemize("Привет, мир"))
```

Provide explicit language and annotations/overrides when routing a foreign span.
