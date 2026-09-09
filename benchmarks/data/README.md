# Synthetic benchmark data

This directory contains synthetic datasets for regression and fallback benchmarks. English
and French dictionary cases use externally provisioned Lexphon `gold` assets. No benchmark
script builds or reads KokoroG2P-owned lexicon files.

## Available datasets

| File | Language |
| --- | --- |
| `en_us_synthetic.json` | US English |
| `en_gb_synthetic.json` | GB English |
| `de_synthetic.json` | German |
| `fr_synthetic.json` | French |
| `ja_synthetic.json` | Japanese |
| `ko_synthetic.json` | Korean |

Validate datasets with:

```bash
python benchmarks/validate_synthetic_data.py --all
```

## External English and French data

Install the runtime assets before running English or French dictionary benchmarks:

```bash
lexphon data install en-us:gold en-gb:gold fr-fr:gold
lexphon data verify en-us:gold en-gb:gold fr-fr:gold
```

Use `lexicons="gold"` for dictionary-backed comparisons and `lexicons=()` for
fallback-only comparisons. The old tiered benchmark matrix has been removed.

## Generate phonemes

```bash
python benchmarks/generate_phonemes.py "Your sentence here."
```

The helper uses the installed external gold asset, then can cross-validate fallback
backends. Review generated output before adding it to a synthetic dataset.

## Dataset format

Each JSON file contains `metadata` and a `sentences` list. Sentence records include text,
expected Kokoro phonemes, a category, and optional notes. Keep expected output tied to the
explicit benchmark mode and document the selected language and Lexphon asset.
