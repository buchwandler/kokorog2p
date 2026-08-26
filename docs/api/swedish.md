# Swedish G2P

Swedish is implemented as a native deterministic rule-based frontend.

```python
from kokorog2p import get_g2p, phonemize
from kokorog2p.sv import phonemize_word_raw

g2p = get_g2p("sv")
print(phonemize("Hej världen!", language="sv").phonemes)
print(phonemize_word_raw("sjuk").ipa)
```

The aliases `sv`, `sv-se`, `swe`, and `swedish` select the same native implementation.
Runtime phonemization contains no Swedish pronunciation dictionary, network access, or
neural model. eSpeak and Goruut are disabled by default and can be requested explicitly
as fallback options.

`phonemize_word_raw()` returns Swedish reference-style IPA. `SwedishG2P` then uses an
explicit adapter for phones not present in the selected Kokoro vocabulary. The external
benchmark compares only the raw result, not adapted Kokoro output.

This is a grapheme-to-pronunciation frontend. Swedish numbers, dates, units,
abbreviations, and spoken semantic normalization remain outside this module. Lexical and
loanword irregularities are expected limitations of a pure rule system.
