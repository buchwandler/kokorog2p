# German multi-lexicon compression experiment

This is an opt-in research harness. It does not change `kokorog2p.de`, never downloads
data on import, and keeps the three sources independent because provenance and licensing
are source-specific.

## Contracts

- **Lookup-semantic lossless** means that for every exact source spelling `W`,
  `asset.lookup_all(W) == source.lookup_all(W)` and the complete word key set is
  identical. Ordered duplicate pronunciation variants are retained.
- This is not physical source-record reconstruction: global TSV row order, original line
  endings, and original line numbers are not part of the runtime asset. An archival
  row-sequence mode would be required for that guarantee.
- **Behavior-lossless** is a separate derived Kokoro-view experiment and cannot
  authorize deletion from raw source data.
- `records_exact` preserves duplicate rows; `runtime_unique` removes only exact
  duplicate IPA values while preserving first-seen order.

Verification reports missing words, extra words, pronunciation mismatches,
variant-count/order mismatches, source and asset SHA-256 values, schema, compressor,
parser, and view versions. Approximate IPA matching never authorizes compression.

## Stable experiment modes

| Mode                              | Description                                  |
| --------------------------------- | -------------------------------------------- |
| `baseline-canonical` / `baseline` | Canonical runtime-equivalent direct mapping  |
| `exact-two-part` (`C1`)           | Exact two-component orthographic composition |
| `exact-multipart` (`C2`)          | Bounded exact multipart composition          |
| `exact-multipart-ids` (`C2I`)     | Integer atom-reference prototype             |
| `ipa-intern` (`P1`)               | Deduplicated complete IPA strings            |
| `ipa-repair-macros` (`P2`)        | Reversible repeated IPA macro experiment     |
| `exact-linkers` (`C3`)            | Opt-in exact German linking candidates       |

P2 and P4 formats remain research assets until their byte, RSS, load-time, and quality
measurements pass predeclared decision gates.

## Quick start

```bash
python -m pytest -q experiments/de_lexicon_compression/tests
python experiments/de_lexicon_compression/download_sources.py --source crane_wiktionary --download
python experiments/de_lexicon_compression/analyze_sources.py --source crane_wiktionary --data-root ~/.cache/kokorog2p/experiments/de-lexicons --output reports/source-analysis
python experiments/de_lexicon_compression/compress.py --source crane_wiktionary --mode exact-multipart --data-root ~/.cache/kokorog2p/experiments/de-lexicons --output reports/crane-multipart
python experiments/de_lexicon_compression/verify.py --run reports/crane-multipart --data-root ~/.cache/kokorog2p/experiments/de-lexicons
```

Large downloads and full matrix benchmarks are manual/opt-in. The `data/` and `reports/`
directories are ignored so third-party assets are not accidentally shipped. Crane
remains CC-BY-SA-4.0 and the gruut/eSpeak-derived source remains `REVIEW_REQUIRED`;
neither is redistributable under only the project license.

## Measurements and reports

The harness compares a canonical lookup baseline and every experiment asset in plain
UTF-8 JSON, gzip, XZ, and wheel-equivalent DEFLATE. Primary distribution metrics are net
DEFLATE savings; installed-size and normalized fresh-process RSS are reported
separately. Runtime workers measure atoms, exceptions, derived entries, misses, and
mixed workloads. Empty categories are reported as `available: false`, not as a fake
lookup.

Reports include source revision/checksum, parser/view/compressor versions, Python and
platform, mode, configuration hash, provenance, licensing, and whether a measurement is
unavailable. Full-source results are not inferred from toy data.

## Boundaries

Do not replace `kokorog2p/de/data/de_gold.json`, modify `kokorog2p/de/lexicon.py` or
`kokorog2p/de/g2p.py`, merge independently licensed sources, use approximate matching,
or make a research representation a production asset without a separate integration
decision.
