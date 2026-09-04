# Language support

KokoroG2P provides language-specific phonological frontends over a common prepared-text
pipeline. Select the language explicitly with `phonemize_prepared()` or `get_g2p()`.
Written-to-spoken semantic preparation is outside every frontend.

## Common contract

```python
from kokorog2p import phonemize_prepared

result = phonemize_prepared("Bonjour le monde", language="fr")
```

All frontends preserve prepared input and expose token-level phonemes. Numbers,
quantities, dates, times, currencies, units, abbreviations, and URLs must be prepared by
the calling application. Language switching is also explicit: use `OverrideSpan` or
annotation language metadata for a known foreign span. No generic automatic detector is
included.

## Native and dictionary frontends

| Language        | Code             | Frontend                     |
| --------------- | ---------------- | ---------------------------- |
| English (US/GB) | `en-us`, `en-gb` | dictionary and rule-based    |
| German          | `de`             | dictionary and rule-based    |
| French          | `fr`             | dictionary and rule-based    |
| Spanish         | `es`             | rule-based                   |
| Italian         | `it`             | rule-based and lexicon       |
| Portuguese      | `pt-br`, `pt-pt` | rule-based                   |
| Czech           | `cs`             | rule-based                   |
| Vietnamese      | `vi`, `vi-vn`    | native rule-based            |
| Swedish         | `sv-se`          | native rule-based            |
| Russian         | `ru`             | LexHint with eSpeak fallback |
| Kazakh          | `kk`             | eSpeak adapter               |
| Hebrew          | `he`             | Phonikud adapter             |
| Arabic          | `ar`             | optional diacritizer adapter |
| Chinese         | `zh`             | pypinyin/Zhuyin frontend     |
| Japanese        | `ja`             | pyopenjtalk or Cutlet        |
| Korean          | `ko`             | LexHint fast path plus g2pK  |
| Thai            | `th`             | LexHint with native fallback |

Install language-specific optional dependencies from the matching extras in
`pyproject.toml`, for example `pip install "kokorog2p[ja]"`.

## Backend and model controls

Use `get_g2p()` for backend-specific options such as `backend`, `voice`, or an
explicitly selected spaCy model. Semantic preparation options and abbreviation
registries are not accepted by the v0.9 API.

```python
from kokorog2p import get_g2p

g2p = get_g2p("en-us", use_spacy=False)
print(g2p.phonemize("Hello world"))
```

## Prepared-language composition

A cross-package pipeline may prepare text and then route the prepared result explicitly:

```python
from spokenform import prepare_for_kokorog2p
from kokorog2p import phonemize_prepared

prepared = prepare_for_kokorog2p("Meeting at 2 kg", language="en").spoken_text
result = phonemize_prepared(prepared, language="en-us")
```

Spokenform is optional and is not imported by the core package.
