# Installation

Install the core package for the prepared-text G2P pipeline:

```bash
python -m pip install kokorog2p
```

The core package does not install or import a semantic text-preparation package. Written
numbers, abbreviations, units, currencies, dates, URLs, and similar forms must be
prepared by the calling application before phonemization.

## Language extras

Language and backend integrations are optional extras:

````bash
python -m pip install "kokorog2p[en]"
python -m pip install "kokorog2p[de]"
python -m pip install "kokorog2p[fr]"

German pronunciation dictionaries are not bundled with KokoroG2P. Install the default data explicitly through Lexphon:

```bash
lexphon data install de-de:gold
lexphon data verify de-de:gold
````

Install optional named layers only when needed:

```bash
lexphon data install de-de:crane de-de:espeak de-de:olaph
```

## Released LexHint data

Russian, Thai, Vietnamese, Japanese, Korean, and Portuguese pronunciation dictionaries
are provisioned through Lexphon and are not bundled or downloaded by KokoroG2P:

```bash
lexphon data install ru:lexhint th:lexhint vi:lexhint ja:lexhint ko:lexhint pt:lexhint
lexphon data verify ru:lexhint th:lexhint vi:lexhint ja:lexhint ko:lexhint pt:lexhint
```

The corresponding language extras only install frontend dependencies. Provision these
assets during image or container construction. German lookup is offline at runtime and
performs no implicit download. python -m pip install "kokorog2p[ko]" python -m pip
install "kokorog2p[ja]" python -m pip install "kokorog2p[espeak]"

````

See `pyproject.toml` for the complete list of language extras. Optional spaCy models are
never downloaded by KokoroG2P; install the model required by your application
separately.

## Optional semantic preparation

If the application uses Spokenform, install and invoke it independently:

```bash
python -m pip install "spokenform>=0.3.5,<0.4"
````

```python
from spokenform import prepare_for_kokorog2p
from kokorog2p import phonemize_prepared

prepared = prepare_for_kokorog2p("Read 2 kg", language="en").spoken_text
result = phonemize_prepared(prepared, language="en-us")
```

## Development installation

```bash
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_prepared_core.py tests/test_dependency_contract.py
```

For release and integration checks, consult the project workflow and keep optional
cross-package tests separate from the Spokenform-free core suite.
