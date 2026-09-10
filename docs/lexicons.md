# External lexicons and release policy

KokoroG2P consumes lexicons provisioned by Lexphon. It does not ship source
dictionaries, pack `.g2lex` assets, generate registries, or validate producer release
files.

## English and French

English and French each expose one logical `gold` lexicon backed by an external asset:

| Language   | Lexphon ID   |
| ---------- | ------------ |
| US English | `en-us:gold` |
| GB English | `en-gb:gold` |
| French     | `fr-fr:gold` |

Provision released data before using the default English or French dictionary path:

```bash
lexphon data install en-us:gold en-gb:gold fr-fr:gold
lexphon data verify en-us:gold en-gb:gold fr-fr:gold
```

`get_g2p("en-us")`, `get_g2p("en-gb")`, and `get_g2p("fr-fr")` select `gold` by default.
Use `lexicons=()` for fallback-only operation. `silver` is not an English runtime
option.

Runtime lookup is offline. KokoroG2P does not fetch catalogs, download assets, invoke
the Lexphon CLI, or rebuild source dictionaries during construction or lookup. Missing
data produces an installation and verification command in the error message.

Released Lexphon catalog entries are the source of truth for these IDs. Install and
verify the requested layers before integration or dictionary-backed release checks.
KokoroG2P does not restore local copies when a catalog entry or asset is unavailable.

## Named German lexicons

German names are application-facing choices backed by externally managed Lexphon IDs:

| Name      | Lexphon ID      | Default |
| --------- | --------------- | ------- |
| `gold`    | `de-de:gold`    | yes     |
| `crane`   | `de-de:crane`   | no      |
| `espeak`  | `de-de:espeak`  | no      |
| `olaph`   | `de-de:olaph`   | no      |
| `lexhint` | `de-de:lexhint` | no      |

Provision them explicitly before using a named dictionary:

```bash
lexphon data install de-de:gold
lexphon data verify de-de:gold
```

Optional layers can be installed when needed:

```bash
lexphon data install de-de:crane de-de:espeak de-de:olaph de-de:lexhint
lexphon data verify de-de:crane de-de:espeak de-de:olaph de-de:lexhint
```

```python
from kokorog2p import available_lexicons, get_g2p

available_lexicons("de")  # ("gold", "crane", "espeak", "olaph", "lexhint")
g2p = get_g2p("de")
g2p = get_g2p("de", lexicons="crane")
g2p = get_g2p("de", lexicons=("gold", "olaph"))
```

For an explicit selection, the first layer containing a word wins. `lexicons="espeak"`
selects the static `de-de:espeak` dictionary and is distinct from
`use_espeak_fallback=True`, which is KokoroG2P's dynamic fallback path.

## Distribution policy

KokoroG2P wheels and source distributions contain no migrated `.g2lex` assets, source
lexicons, manifests, generated registries, or lexicon notice bundles. Data provenance
and release metadata belong to `g2lex-data` and Lexphon.

## Swedish NST lexicon

The Swedish NST lexicon is produced and published by `g2lex-data` and installed
explicitly through Lexphon. Swedish rules remain the default.

```bash
lexphon data install sv-se:nst
lexphon data verify sv-se:nst
```
