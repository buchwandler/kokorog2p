# Russian API

Russian is provided by the native `RussianG2P` frontend. It targets the stock Kokoro 1.0
vocabulary and keeps token offsets in the original source text.

```python
from kokorog2p import get_g2p

g2p = get_g2p("ru")
tokens = g2p("Это русский текст.")
```

The default `accentuator="auto"` uses RUAccent lazily for sentence-level stress, ё
restoration, and contextual homographs. Install the optional extra first:

```bash
pip install "kokorog2p[ru]"
```

RUAccent and its model artifacts can be large. They are not imported or loaded by
`import kokorog2p`, and model loading starts only when an instance is used. A missing
installation produces an actionable optional-dependency error.

## Explicit stress

For text that already contains combining acute stress, bypass the contextual model with
`phonemize_accented`:

```python
explicit = get_g2p("ru", accentuator="none", strict_stress=False)
tokens = explicit.phonemize_accented("за́мок")
```

The canonical annotation is U+0301 immediately after the stressed Cyrillic vowel. The
legacy `+`-before-vowel form is accepted at this boundary and is normalized to combining
acute.

## eSpeak data

Russian uses raw eSpeak IPA and verifies at runtime that the selected Russian data
honors explicit combining-acute stress. A custom data directory can be provided through
the factory:

```python
g2p = get_g2p("ru", espeak_data="/path/to/espeak-ng-data")
```

If the capability probe fails in strict mode, configure a compatible eSpeak-ng
installation rather than silently losing stress information. The compiled `espeak-data`
from external Russian projects is not distributed by KokoroG2P.

## Latin and punctuation

Russian and punctuation tokens retain original text and offsets. The default
`latin_policy="preserve"` keeps Latin source tokens without pretending they are Russian
phonemes. Use `latin_policy="drop"` when a downstream pipeline explicitly wants them
marked as dropped. Brackets are normalized through the shared punctuation pipeline and
do not become phoneme vocabulary symbols.

Russian-specific number and abbreviation expansion remains owned by the shared
`spokenform` and `abbr2words` pipeline where supported.
