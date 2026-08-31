# Lexicon assets and release policy

KokoroG2P keeps canonical lexicon sources outside the importable package. Runtime code
opens only generated `.g2lex` resources through `importlib.resources`; it never
downloads or reads canonical source files.

## Named German lexicons

The German registry contains four names:

| Name     | Default | Encoding | Upstream                     | Notes                                    |
| -------- | ------- | -------- | ---------------------------- | ---------------------------------------- |
| `gold`   | yes     | IPA      | KokoroG2P legacy source      | Compatibility default                    |
| `crane`  | no      | IPA      | Crane German Wiktionary      | Ordered IPA variants                     |
| `espeak` | no      | IPA      | CSTR `g2p-dicts`             | Bundled static eSpeak-derived dictionary |
| `olaph`  | no      | IPA      | CSTR redistribution of OLaPh | Large MIT-licensed dictionary            |

`gold` is the only implicit German layer. `crane`, `espeak`, and `olaph` are opt-in. For
an explicit `lexicons=(...)` selection, the first layer containing a word wins. This
order is caller-defined and is not changed by provider, rating, coverage, or source
size.

```python
from kokorog2p import available_lexicons, get_g2p

available_lexicons("de")  # ("gold", "crane", "espeak", "olaph")
get_g2p("de")  # gold only
get_g2p("de", lexicons="crane")
get_g2p("de", lexicons="espeak")
get_g2p("de", lexicons="olaph")
get_g2p("de", lexicons=("gold", "olaph"))
```

`espeak` is a static packaged dictionary and is unrelated to `use_espeak_fallback=True`.
All named lexicons work offline. German source IPA is converted by the strict Kokoro
consumer. Unsupported pronunciations are rejected without silent deletion and may fall
through to configured fallback.

## German IPA consumer contract

German assets store source-ordered IPA variants losslessly. The consumer selects the
first variant and applies its target-profile conversion. Mapped affricates and
diphthongs use the established Kokoro tokens, explicit source marks are classified as
ignored, and unsupported material remains visible and invalid. An invalid or empty first
pronunciation cannot suppress fallback.

## Distribution policy

The wheel contains generated `.g2lex` assets and
`kokorog2p/lexicons/data/THIRD_PARTY_NOTICES.md`, but not canonical source data. The
source distribution follows the same generated-asset-centric policy: `lexicons/sources/`
is excluded, including the large CSTR dictionaries. Provenance and license notices
remain included for redistributed third-party assets. See
`lexicons/sources/de/PROVENANCE.md` for exact revisions, hashes, import policies, and
attribution.
