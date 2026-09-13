# KokoroG2P examples

These scripts demonstrate the current prepared-text API. KokoroG2P receives speakable,
semantically prepared text; it does not expand dates, abbreviations, units, currencies,
URLs, or other written semantics.

Run examples from the repository root with `python examples/<name>.py`. Scripts never
install or download dependencies, dictionaries, models, or provider data. Provision
external resources with the commands listed below first.

| Example                      | Demonstrates                                                                        | Extra requirements                                                                                             |
| ---------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `new_api_demo.py`            | Prepared API, phoneme overrides, duplicate spans, language spans, and snap warnings | Resources/providers used by the script                                                                         |
| `explicit_language_spans.py` | Explicit language routing with `OverrideSpan`                                       | Resources for routed languages                                                                                 |
| `mixed_language_auto.py`     | Conservative automatic German/English routing                                       | Lexical evidence data; eSpeak if fallback is enabled                                                           |
| `marker_demo.py`             | Marker parsing and marker-derived overrides                                         | Resources/providers used by the selected demos                                                                 |
| `debug_mode_demo.py`         | English debug and provenance diagnostics                                            | English setup; spaCy only if enabled                                                                           |
| `demo_both_features.py`      | Prepared text plus explicit pronunciation/language overrides                        | Resources for selected language(s)                                                                             |
| `lexicon_selection.py`       | Named lexicon discovery, metadata, explicit selection, and evidence                 | `python -m pip install "kokorog2p[de]"`; `lexphon data install de-de:crane`; `lexphon data verify de-de:crane` |
| `espeak_fallback.py`         | Dynamic eSpeak fallback after a forced dictionary miss, with provenance             | `python -m pip install "kokorog2p[espeak]"`; system `espeak-ng` or `espeak` on `PATH`                          |
| `result_inspection.py`       | `PhonemizeResult`, source offsets, phonemes, warnings, and model token IDs          | Base install                                                                                                   |
| `structured_stress.py`       | Structured `+2` and `-2` stress overrides                                           | Base install                                                                                                   |
| `cache_and_batch.py`         | Factory cache identity, diagnostics, and frontend reuse for batches                 | Base install                                                                                                   |
| `external_annotations.py`    | Caller-provided `TokenAnnotation` POS/tag data without spaCy                        | `en-us:gold`; install with `lexphon data install en-us:gold` and verify it                                     |

## Provider distinction

`lexicons="espeak"` selects the static German `de-de:espeak` lexicon. It is not the same
as `use_espeak_fallback=True`, which configures the dynamic Lexphon eSpeak provider to
run after a lexical lookup miss. The fallback example uses `lexicons=()` to make that
provider path deterministic.

## Optional resources

Lexphon assets and system executables are managed outside Python. For the named-lexicon
example:

```bash
python -m pip install "kokorog2p[de]"
lexphon data install de-de:crane
lexphon data verify de-de:crane
python examples/lexicon_selection.py
```

For dynamic eSpeak fallback:

```bash
python -m pip install "kokorog2p[espeak]"
# Install espeak-ng or espeak using the operating system package manager.
python examples/espeak_fallback.py
```

Dependency-light examples:

```bash
python examples/result_inspection.py
python examples/structured_stress.py
python examples/cache_and_batch.py
```
