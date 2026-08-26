# Vietnamese API

`kokorog2p` provides a native pure-Python Vietnamese frontend under the canonical
language code `vi-vn`. The aliases `vi`, `vie`, and `vietnamese` resolve to the same
frontend.

```python
from kokorog2p import get_g2p, phonemize

g2p = get_g2p("vi", foreign_fallback="english")
print(g2p.phonemize("Xin chào!"))
result = phonemize("Xin chào!", language="vi", return_ids=True)
print(result.phonemes, result.token_ids)
```

The first profile is broad Northern/Hanoi Vietnamese. Each whitespace-separated syllable
is parsed as onset, optional medial `/w/`, nucleus, coda or off-glide, and one named
tone. The six tones are `ngang`, `huyen`, `hoi`, `nga`, `sac`, and `nang`.

Input is normalized to NFC for rule processing while source text and token positions
remain source-oriented. NFC and NFD spellings have identical pronunciation. Vietnamese
vowel-quality marks are retained during tone extraction.

Invalid Vietnamese spellings are not guessed. With `foreign_fallback="english"` (the
default), tokens that fail structural Vietnamese parsing use the existing lazy English
frontend. `"espeak"` and `"none"` are also supported. Use `strict=True` to raise when no
fallback pronunciation is available.

The model profile uses Kokoro's supported characters and tone arrows directly.
`validate_output()` and `encode_output()` in `kokorog2p.vi.model_profile` expose
explicit model checks. The frontend does not add a `vig2p` dependency and does not
implement a second semantic number, date, URL, or currency normalizer.

See [Vietnamese provenance](../vi/PROVENANCE.md) for independent linguistic sources and
clean-room boundaries.
