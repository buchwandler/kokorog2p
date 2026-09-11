# Hindi G2P

Hindi is a prepared-text eSpeak-NG frontend targeting the stock Kokoro v1.0 model.

## Installation

```bash
python -m pip install "kokorog2p[hi]"
```

The extra uses the existing eSpeak integration. No Hindi Lexphon or G2Lex data is
bundled or required.

## Supported aliases

The aliases `hi`, `hi-in`, `hi_IN`, `hin`, and `hindi` normalize to canonical language
`hi-in`. All aliases share the same cached `HindiG2P` instance when factory options
match.

```python
from kokorog2p import get_g2p, phonemize_prepared

g2p = get_g2p("hi")
assert g2p is get_g2p("hindi")

result = phonemize_prepared(
    "नमस्ते दुनिया!",
    language="hi",
    return_ids=True,
)
assert result.phonemes
assert result.token_ids
```

## Raw IPA and model compatibility

`HindiG2P` uses the eSpeak-NG `hi` voice and requests raw IPA. It does not call the
English-oriented `from_espeak()` conversion because that conversion would alter Hindi
vowel quality, length, nasalization, and consonant distinctions. The Hindi profile only
strips eSpeak language markers and tie controls and removes unsupported U+0329
syllabicity. The final output is validated against the Kokoro v1.0 vocabulary.

`strict=True` reports an unsupported symbol with the source token, raw IPA, and
normalized IPA. With `strict=False`, an invalid lexical token is returned without
phonemes instead of emitting an invalid model input.

## Lazy initialization and routing

Factory construction is lazy. Creating `get_g2p("hi")` does not initialize eSpeak-NG;
the backend is created on first pronunciation. Explicit `backend="espeak"` selects the
same Hindi-safe frontend.

Hindi has no runtime lexicon and does not provide positive automatic-routing evidence.
Its eSpeak pronunciation is realization data only. Use explicit language or language
spans when composing Hindi with other prepared languages.
