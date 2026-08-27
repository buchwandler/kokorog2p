# Crane held-out G2P benchmark

This benchmark measures `kokorog2p` against an external, held-out word-to-IPA fixture
for US English (`en_US`) and German (`de_DE`). It is deliberately separate from the
checked-in synthetic sentence benchmarks. The fixture is used for measurement only and
must not be copied into package lexica or model data.

## Source and provenance

- Dataset:
  [`crane-local-ai/test-data`](https://huggingface.co/datasets/crane-local-ai/test-data)
- Pinned revision: `19b6ea610af45d9258a3957c7a22694280bdf145`
- Files: `g2p/en_us/test.tsv`, `g2p/de_de/test.tsv`, the shared `g2p/kokoro_vocab.json`,
  and both normalizer reference files.
- Each language test file contains 5,000 held-out word-to-IPA rows. The dataset card
  describes random seed 42 samples from Moonshine Voice lexica, with source lineage to
  CMUdict for English.

The benchmark code pins SHA-256 values for all five assets and checks them before a run.
Review the upstream dataset card for its current license and attribution obligations
before redistributing data or results. This repository does not package the external
fixture.

## Acquisition

An existing checkout or extracted directory can be used without network access:

```bash
python benchmarks/benchmark_crane_test_data.py \
  --data-root /path/to/test-data \
  --language all
```

The directory must contain:

```text
g2p/kokoro_vocab.json
g2p/en_us/test.tsv
g2p/en_us/kokoro_normalizer_ref.tsv
g2p/de_de/test.tsv
g2p/de_de/kokoro_normalizer_ref.tsv
```

Downloading is explicit and uses the pinned revision. Missing data never causes an
implicit download:

```bash
python benchmarks/benchmark_crane_test_data.py --download --language all
```

The default cache is `~/.cache/kokorog2p/benchmarks/crane-test-data/<revision>/`.
Downloads use temporary files, verify their checksum, and then atomically replace the
target. `--limit` is available for development runs; an unrestricted language run
requires exactly 5,000 rows.

## Normalization and comparison policy

The fixture contains raw IPA, while `kokorog2p` emits Kokoro phoneme characters. The
benchmark independently converts only the reference side using the supplied vocabulary
and documented mappings. English mappings include diphthongs, affricates, rhotic vowels,
and stress-preserving transformations. German mappings include `ʦ`, `ʣ`, `S`,
diphthongs, `ʏ`, syllabic consonants, and tie-marker handling.

Before scoring, every supplied normalizer reference row must match both its expected
normalized string and its expected token IDs. English therefore requires 71/71 cases and
German 32/32 cases. A mismatch aborts the scored run.

The actual side receives only Unicode NFC normalization and whitespace collapsing.
Stress, length, affricates, diphthongs, and unknown output are not silently normalized
away. Punctuation token phonemes are excluded, while lexical pronunciation parts retain
their order and are joined with one ASCII space.

## Metrics

The primary score is corpus character error rate:

```text
CER = sum(entry edit distance) / sum(reference character count)
```

Reports also include exact-match rate, exact matches, total edit distance, reference
characters, conversion exceptions, elapsed time, words per second, normalizer case
counts, and deterministic worst mismatch examples. Conversion exceptions remain in the
denominator with empty actual output. The runner does not add a quality threshold or
pass/fail accuracy gate.

## Commands

```bash
# Help and local development sample
python benchmarks/benchmark_crane_test_data.py --help
python benchmarks/benchmark_crane_test_data.py \
  --data-root /path/to/test-data --language en_US --limit 100 --verbose

# Full language run with JSON output
python benchmarks/benchmark_crane_test_data.py \
  --data-root /path/to/test-data --language de_DE \
  --output crane_de_DE.json
```

The JSON records the dataset revision, selected profile, normalizer validation, metrics,
and worst cases. It does not include the external fixture itself.

## Interpretation and leakage rule

This is an accuracy measurement and diagnostic tool, not a replacement for the synthetic
benchmarks. Inspect worst cases to distinguish G2P errors, pronunciation variants,
representation differences, and backend environment differences before making changes.

The two `test.tsv` files are evaluation-only. Never merge them into `en_gold`,
`en_silver`, German lexicon assets, or other production lookup data. Do not special-case
their words. Improvements motivated by this benchmark must be general linguistic rules,
normalization fixes, or independently sourced lexicon corrections. The benchmark remains
useful only while its target pronunciations remain held out.
