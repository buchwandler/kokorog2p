# German multi-lexicon compression experiment

This is an opt-in research harness. It does not change `kokorog2p.de` and never
downloads data on import. The three sources remain independent because provenance and
licensing are source-specific.

## Contracts

- **Source-semantic lossless** means exact source spellings, codepoints, duplicate rows,
  and ordered pronunciation variants round-trip.
- **Behavior-lossless** is a separate derived Kokoro-view experiment and cannot
  authorize deletion from raw source data.
- `records_exact` preserves duplicate rows; `runtime_unique` removes only exact
  duplicate IPA values, preserving first-seen order.

## Quick start

```bash
python -m pytest -q experiments/de_lexicon_compression/tests
python experiments/de_lexicon_compression/download_sources.py --source crane_wiktionary --download
python experiments/de_lexicon_compression/analyze_sources.py --source crane_wiktionary --data-root ~/.cache/kokorog2p/experiments/de-lexicons --output reports/source-analysis
python experiments/de_lexicon_compression/compress.py --source crane_wiktionary --mode exact-multipart --data-root ~/.cache/kokorog2p/experiments/de-lexicons --output reports/crane-multipart
python experiments/de_lexicon_compression/verify.py --run reports/crane-multipart --data-root ~/.cache/kokorog2p/experiments/de-lexicons
```

Large downloads, full benchmarks, and the matrix are manual/opt-in. The `data/` and
`reports/` directories are ignored so third-party assets are not accidentally shipped.
The gruut/eSpeak-derived source remains `REVIEW_REQUIRED`; Crane data remains CC
BY-SA-4.0 and is not redistributable under only the project license.

## Matrix and reports

`analyze_sources.py` writes source statistics, casing/Unicode collisions,
overlap/conflicts, reachability, and baseline plain/gzip/xz measurements. Compression
runs contain `summary.json`, deterministic atom/exception/derived TSVs, failures,
verification, size breakdown, and `compressed.asset`. `benchmark_quality.py`,
`benchmark_runtime.py`, and `run_matrix.py` emit JSON/TSV and use isolated subprocesses
where data size warrants it.

The first exact modes are `exact-two-part` (C1) and `exact-multipart` (C2). They use
deterministic source-semantic equality only. Linguistic join rules, merged source
stores, production APIs, neural G2P, and custom binary/mmap formats are intentionally
deferred until measurements justify them.
