# Korean API

KoreanG2P applies g2pK phonological rules and optional morphology to prepared Korean
text. It does not convert Arabic numerals, Latin words, abbreviations, units, or
currencies. Those semantics must be prepared before calling the frontend.

```python
from kokorog2p.ko import KoreanG2P

g2p = KoreanG2P(use_dict=False)
print(g2p.phonemize("안녕하세요"))
```

Install `kokorog2p[ko-mecab]` only when morphology/POS analysis is required. The core
Korean frontend has no Spokenform or semantic-preparation dependency.
