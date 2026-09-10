# Installation

## Core installation

Install the prepared-text G2P pipeline:

```bash
python -m pip install kokorog2p
```

KokoroG2P does not expand written semantics such as numbers, abbreviations, units,
currencies, dates, or URLs. Prepare those forms in the calling application before
phonemization.

The default English and French dictionary layers are external Lexphon data. Provision
them explicitly when dictionary lookup is needed:

```bash
lexphon data install en-us:gold en-gb:gold fr-fr:gold
lexphon data verify en-us:gold en-gb:gold fr-fr:gold
```

For fallback-only operation, pass `lexicons=()` and no dictionary data is required.

## Optional language and backend extras

Install only the integrations used by the application:

```bash
python -m pip install "kokorog2p[en]"
python -m pip install "kokorog2p[de]"
python -m pip install "kokorog2p[fr]"
python -m pip install "kokorog2p[ja]"
python -m pip install "kokorog2p[ko]"
python -m pip install "kokorog2p[espeak]"
python -m pip install "kokorog2p[goruut]"
```

Optional spaCy models and system tools such as `espeak-ng` are installed separately.
KokoroG2P never downloads models or dictionary assets during construction or lookup.

## Released Lexphon dictionaries

German named layers are external data:

```bash
lexphon data install de-de:gold de-de:crane de-de:espeak de-de:olaph de-de:lexhint
lexphon data verify de-de:gold de-de:crane de-de:espeak de-de:olaph de-de:lexhint
```

Released LexHint layers for other frontends are provisioned in the same way:

```bash
lexphon data install ru:lexhint th:lexhint vi:lexhint ja:lexhint ko:lexhint pt:lexhint
lexphon data verify ru:lexhint th:lexhint vi:lexhint ja:lexhint ko:lexhint pt:lexhint
```

Set `LEXPHON_DATA_HOME` when data must live in an isolated image or CI workspace.
Integration tests additionally require `KOKOROG2P_EXTERNAL_LEXPHON_DATA=1`.

## Optional semantic preparation

Spokenform is a separate package for applications that need semantic expansion:

```bash
python -m pip install "spokenform>=0.3.5,<0.4"
```

```python
from spokenform import prepare_for_kokorog2p
from kokorog2p import phonemize_prepared

prepared = prepare_for_kokorog2p("Read 2 kg", language="en").spoken_text
result = phonemize_prepared(prepared, language="en-us")
```

Spokenform is not a core or core-test dependency.

## Development installation

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Bare pytest uses the safe core selection. It excludes integration, spaCy, slow, and
resource-heavy tests. Use the canonical bounded runner for broader execution:

```bash
python tools/run_test_suite.py --profile full --batch-size 4 --max-rss-mb auto
python tools/run_test_suite.py --profile full --include-integration --max-rss-mb auto
```

The full and integration profiles require the released Lexphon data listed above. Use
`--list-plan` to inspect the deterministic plan before execution. Coverage runs through
the same sequential runner with `--coverage`; it combines subprocess data before
producing `coverage.xml`.
