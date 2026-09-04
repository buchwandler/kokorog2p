# Lexicon assets and release policy

KokoroG2P packages only the generated G2Lex assets it still owns. Runtime code opens
those resources through `importlib.resources`; it never downloads or reads canonical
source files.

## Named German lexicons

German names are application-facing choices backed by externally managed Lexphon IDs:

| Name     | Lexphon ID     | Default |
| -------- | -------------- | ------- |
| `gold`   | `de-de:gold`   | yes     |
| `crane`  | `de-de:crane`  | no      |
| `espeak` | `de-de:espeak` | no      |
| `olaph`  | `de-de:olaph`  | no      |

German datasets are produced and published by `g2lex-data`. KokoroG2P does not contain,
generate, audit, or redistribute these dictionaries. Provision them explicitly before
using a named dictionary:

```bash
python -m pip install kokorog2p
lexphon data install de-de:gold
lexphon data verify de-de:gold
```

Install optional layers explicitly when needed:

```bash
lexphon data install de-de:crane de-de:espeak de-de:olaph
lexphon data verify de-de:crane de-de:espeak de-de:olaph
```

Runtime lookup is offline. `get_g2p()` and ordinary German phonemization never fetch a
catalog, download an asset, invoke the Lexphon CLI, or build a source dictionary.
Missing selected data raises an actionable installation error. Use `use_lexicon=False`
for fallback-only operation without German Lexphon data.

```python
from kokorog2p import available_lexicons, get_g2p

available_lexicons("de")  # ("gold", "crane", "espeak", "olaph")
g2p = get_g2p("de")  # logical default: gold
g2p = get_g2p("de", lexicons="crane")
g2p = get_g2p("de", lexicons=("gold", "olaph"))
```

For an explicit selection, the first layer containing a word wins. Caller order is not
changed by provider, rating, coverage, or catalog order. `lexicons="espeak"` selects the
static `de-de:espeak` dictionary and is distinct from `use_espeak_fallback=True`, which
is KokoroG2P's dynamic fallback path.

KokoroG2P retains German tag mapping, case handling, ordered primary variants, strict
IPA-to-Kokoro conversion, stress controls, source/rating policy, and fallback behavior.
The German adapter passes generic selectors such as `DET` and `PRON` to Lexphon;
Kokoro's spaCy `ART` mapping remains in KokoroG2P.

## Packaged lexicons

`lexicons/manifest.toml` and `lexicons/lock.json` describe only packaged assets owned by
KokoroG2P. Regenerate and validate them with:

```bash
python scripts/build_g2lex_assets.py --all
python scripts/build_g2lex_assets.py --check
python scripts/validate_g2lex_assets.py --all
```

The generated registry contains only packaged-resource specifications. German external
specifications are kept separate and are never passed to the packaged-resource opener.

## Distribution policy

Wheels contain the remaining generated `.g2lex` assets and the third-party notice file.
They do not contain German dictionaries, German source data, or German producer audits.
Source distributions exclude canonical lexicon sources. German data provenance and
release metadata belong to `g2lex-data` and Lexphon.

## Swedish NST lexicon

The Swedish NST lexicon is produced and published by `g2lex-data` and installed
explicitly through Lexphon. KokoroG2P does not package or redistribute the source TSV or
generated G2Lex asset. Swedish rules remain the default.

```bash
lexphon data install sv-se:nst
lexphon data verify sv-se:nst
```

For direct lookup, use the installed Lexphon data explicitly:

```python
from lexphon import Phonemizer

with Phonemizer("sv", lexicons=("sv-se:nst",), fallback=None) as phonemizer:
    pronunciation = phonemizer.lookup("hej")
```
