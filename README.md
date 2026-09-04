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

Automatic document-language detection and mixed-language segmentation are outside the
core package. Applications should identify foreign spans and route them explicitly.

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
