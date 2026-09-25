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
lexphon data install en-us:gold en-us:lexhint en-gb:gold en-gb:lexhint
lexphon data verify en-us:gold en-us:lexhint en-gb:gold en-gb:lexhint
```

Use `get_g2p("en-us")` or `get_g2p("en-gb")` for factory construction. The frontend
preserves supplied text and token offsets; semantic preparation belongs to the caller.

## Lexicon controls

English exposes `gold` and an explicitly selected `lexhint` source. Gold values use the
`kokoro-v1` encoding; LexHint values use IPA and pass through the same English
realization profile after decoding. Use `lexicons=()` for fallback-only operation. There
is no English silver tier or runtime API for loading packaged dictionaries. `use_spacy`
and explicit local model settings control optional POS-aware tokenization.
