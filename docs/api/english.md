# English API

The English frontend phonemizes prepared English text with the shipped lexicons and
optional backend/model controls. It does not expand numbers, currencies, dates, units,
or abbreviations.

```python
from kokorog2p.en import EnglishG2P

g2p = EnglishG2P(language="en-us", use_spacy=False)
print(g2p.phonemize("Hello world"))
```

Use `get_g2p("en-us")` for factory construction. The frontend preserves supplied text
and token offsets; semantic preparation belongs to the caller.

## Lexicon controls

`load_gold` and `load_silver` control the shipped dictionary tiers. `use_spacy` and
explicit local model settings control optional POS-aware tokenization. No semantic
preparation package is imported by this frontend.
