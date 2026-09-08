# kokorog2p

Multilingual grapheme-to-phoneme and Kokoro model adaptation for prepared text.

## v0.9 responsibility boundary

KokoroG2P consumes **prepared, speakable text**. The core owns tokenization, intrinsic
phonological normalization, explicit language routing, annotations, overrides, and
Kokoro phoneme/model output.

The core does **not** verbalize numbers, abbreviations, units, currencies, dates, times,
URLs, versions, or other written semantics. Prepare those forms in the owning
application or an optional cross-package tool, then call `phonemize_prepared()`.

KokoroG2P has no runtime dependency on Spokenform and its behavior is unchanged by
Spokenform being installed.

## Installation

```bash
python -m pip install kokorog2p
```

Language and backend integrations are optional:

```bash
python -m pip install "kokorog2p[en]"
python -m pip install "kokorog2p[de]"
python -m pip install "kokorog2p[fr]"
python -m pip install "kokorog2p[ko]"
python -m pip install "kokorog2p[ja]"
python -m pip install "kokorog2p[espeak]"
```

German dictionaries are no longer bundled. Install the Lexphon runtime data explicitly
before German dictionary lookup:

```bash
lexphon data install de-de:gold
lexphon data verify de-de:gold
```

Optional named dictionaries use the same explicit provisioning flow. Runtime German
lookup is offline and never downloads data implicitly.

See [Installation](docs/installation.md) for development and optional integration setup.

## Quick start

```python
from kokorog2p import phonemize_prepared

result = phonemize_prepared("Hello world!", language="en-us")
print(result.phonemes)
```

`phonemize()` remains an equivalent prepared-text entry point. The input text is
retained as the coordinate space for tokens and offsets.

## Semantic preparation composition

Use an external preparation package only when written semantics need expansion:

```python
from spokenform import prepare_for_kokorog2p
from kokorog2p import phonemize_prepared

prepared = prepare_for_kokorog2p("Meet Dr. Smith at 2 kg.", language="en").spoken_text
result = phonemize_prepared(prepared, language="en-us")
```

Install Spokenform separately. It is not required for core installation or core tests.

## Explicit language routing

```python
from kokorog2p import OverrideSpan, phonemize_prepared

text = "Hello Welt"
start = text.index("Welt")
result = phonemize_prepared(
    text,
    language="en-us",
    overrides=[OverrideSpan(start, start + 4, {"lang": "de"})],
)
```

## Exact sub-token spans and automatic routing

Use `overlap="split"` when a language span covers part of one orthographic token:

```python
from kokorog2p import OverrideSpan, phonemize_prepared

result = phonemize_prepared(
    "Manpowerdiskussion",
    language="de",
    overlap="split",
    overrides=[OverrideSpan(0, 8, {"lang": "en"})],
    return_ids=False,
)
```

Automatic routing is opt-in and restricted to the configured candidates:

```python
result = phonemize_prepared(
    text,
    language="de",
    language_routing={"mode": "auto", "languages": ["de", "en"]},
    target_model="1.0",
 )
```

The candidate list is a hard allowlist. KokoroG2P still requires the explicit
document/default language; this option only routes individual pronunciation fragments.
The canonical candidate inventory is `en-us`, `en-gb`, `de-de`, `fr-fr`, `es-es`,
`it-it`, `pt-br`, `pt-pt`, `cs-cz`, `zh`, `ja-jp`, `ko-kr`, `vi-vn`, `sv-se`, `he`,
`ar`, `ru-ru`, `kk`, and `th-th`. Aliases are normalized before the allowlist is
applied.

Evidence comes only from the effective selected lexical resources through
`LexiconEvidence`:

- Packaged G2Lex evidence: English US, English GB, and French.
- Provisioned Lexphon evidence: German, Portuguese BR/PT, Russian, Thai, Vietnamese,
  Japanese, Korean, and Swedish when NST is explicitly selected.
- Native frontends without a selected evidence resource: Spanish, Italian, Czech,
  Hebrew, Arabic, Chinese, and Kazakh. These frontends phonemize normally but cannot
  positively claim foreign ownership through automatic routing.

A spelling present in multiple selected stacks remains in the default language, and
unresolved or ambiguous text also remains there. Generic lookup, rules, eSpeak, Goruut,
pypinyin, Phonikud, g2pK, pyopenjtalk, and fallback pronunciation are not evidence.
Explicit `ph`, `phonemes`, `lang`, and `language` spans outrank automatic routing.

A `g2p_resolver(language)` can supply and cache the caller's configured frontends.
Without one, foreign frontends use their own defaults and do not inherit the default
language's lexicons or language-specific options. `target_model` fixes the output
vocabulary and rejects incompatible automatic candidates without changing the model.
Routing changes only G2P frontend selection. KokoroG2P does not select an acoustic
model. `PhonemizeResult.language_routes` contains structured route fragments and
provenance.

For German-default DE/EN routing, default-language ownership remains conservative. If
the selected German Lexphon resource marks foreign pronunciation material with
structured `pronunciation_language_markers`, a pair-specific analyzer may authorize a
stronger mixed-language route for a unique compatible English candidate. KokoroG2P
consumes this marker API and clean IPA; it does not parse Lexphon's raw source
pronunciation notation.

## Annotations

Precomputed linguistic annotations can be supplied without installing a parser:

```python
from kokorog2p import TokenAnnotation, phonemize_prepared

result = phonemize_prepared(
    "record this record",
    language="en-us",
    annotations=[TokenAnnotation(0, 6, "record", pos="NOUN", tag="NN")],
)
```

Annotation offsets are ordered, non-overlapping, half-open offsets into the prepared
text.

## Generic pronunciation providers

When `use_espeak_fallback` or `use_goruut_fallback` is enabled, supported native frontends use Lexphon 0.2 for generic provider execution. `use_cli` is retained for direct backend compatibility and does not select the Lexphon provider path.

Provider output is clean IPA and is converted to the target Kokoro vocabulary by each language frontend. Provider results are realization data, not lexical routing evidence. Install provider extras explicitly when needed:

```bash
python -m pip install "kokorog2p[espeak]"
python -m pip install "kokorog2p[goruut]"
```

Direct `backend="espeak"` and `backend="goruut"` remain available as compatibility paths. Lexphon data installation is also explicit; KokoroG2P does not provision dictionaries automatically.

## Supported languages

English (`en-us`, `en-gb`), German (`de`), French (`fr`), Spanish (`es`), Italian
(`it`), Portuguese (`pt-br`, `pt-pt`), Czech (`cs`), Chinese (`zh`), Japanese (`ja`),
Korean (`ko`), Vietnamese (`vi`), Swedish (`sv-se`), Hebrew (`he`), Arabic (`ar`),
Russian (`ru`), Kazakh (`kk`), and optional Thai (`th`) are supported by
language-specific frontends. See [Language support](docs/languages.md).

Russian, Thai, Vietnamese, Japanese, Korean, and Portuguese pronunciation uses released
LexHint dictionaries provisioned separately through Lexphon. KokoroG2P does not bundle
or download these assets. See [installation](docs/installation.md).

## API and migration guides

- [Quick Start](docs/quickstart.md)
- [Prepared phonemization](docs/prepared_phonemization.md)
- [Core API](docs/api/core.md)
- [Language support](docs/languages.md)
- [Span guide](docs/spans.md)
- [Advanced usage](docs/advanced.md)

## Migration from 0.8.x

In 0.8.x, callers could pass written text directly to the main API:

```python
result = phonemize("Meet Dr. Smith at 2 kg.")
```

In 0.9.0, prepare written semantics in the owning application and pass the result with
an explicit language:

```python
from spokenform import prepare_for_kokorog2p
from kokorog2p import phonemize_prepared

prepared = prepare_for_kokorog2p(
    "Meet Dr. Smith at 2 kg.", language="en"
).spoken_text
result = phonemize_prepared(prepared, language="en-us")
```

Remove `input_mode`, `migrated_semantics`, semantic expansion flags, and
abbreviation-registry calls.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_prepared_core.py tests/test_dependency_contract.py
```

The default core suite is Spokenform-free. Optional cross-package composition coverage
is kept in `tests/test_spokenform_composition.py` and the corresponding CI job.
