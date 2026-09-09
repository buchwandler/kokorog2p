# English API

The English frontend phonemizes prepared English text with an externally provisioned
Lexphon dictionary and optional backend/model controls. It does not expand numbers,
currencies, dates, units, or abbreviations.

```python
from kokorog2p.en import EnglishG2P

g2p = EnglishG2P(language="en-us", lexicons="gold", use_spacy=False)
print(g2p.phonemize("Hello world"))
```

Install the selected asset before construction:

```bash
lexphon data install en-us:gold en-gb:gold
lexphon data verify en-us:gold en-gb:gold
```

Use `get_g2p("en-us")` or `get_g2p("en-gb")` for factory construction. The frontend
preserves supplied text and token offsets; semantic preparation belongs to the caller.

## Lexicon controls

English exposes one logical `gold` selection backed by an external Lexphon asset. Use
`lexicons=()` for fallback-only operation. There is no English silver tier and no
runtime API for loading or selecting packaged dictionaries. `use_spacy` and explicit
local model settings control optional POS-aware tokenization.
