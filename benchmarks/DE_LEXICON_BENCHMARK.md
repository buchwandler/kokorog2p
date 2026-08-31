# German lexicon benchmark evidence

The benchmark was run with 1,000 rows from the pinned Crane local-AI fixture and the
four packaged German assets. The JSON output is retained in
`benchmarks/de_lexicon_sources_results.json`.

## Individual sources

| Source   | Coverage | Target validity | Lookup words/s | Cold open ms | Resident memory delta | Asset bytes |
| -------- | -------: | --------------: | -------------: | -----------: | --------------------: | ----------: |
| `gold`   |    0.949 |           1.000 |         13,273 |        12.18 |             8,622,080 |   8,551,708 |
| `crane`  |    0.978 |           1.000 |         14,824 |         7.69 |            11,083,776 |  10,396,748 |
| `espeak` |    0.977 |           1.000 |         16,032 |         5.88 |             8,327,168 |   7,781,220 |
| `olaph`  |    0.995 |           1.000 |         16,208 |        10.15 |            13,692,928 |  12,898,060 |

Target validity in this table is measured for the sampled fixture rows. The complete
source audits record all source rows and rejected values. eSpeak has 667,295 logical
entries and no invalid first pronunciations. OLaPh has 965,839 logical entries,
1,123,259 physical rows, and 33,387 invalid first pronunciations under its documented
fallback policy.

## Requested precedence stacks

The benchmark evaluates every permutation of the four supplied layers. The requested
stacks produced these results:

| Stack                              | Coverage | Selected exact | Oracle variant exact |
| ---------------------------------- | -------: | -------------: | -------------------: |
| `gold -> crane -> espeak -> olaph` |    0.999 |          0.323 |                0.936 |
| `gold -> crane -> olaph -> espeak` |    0.999 |          0.323 |                0.936 |
| `gold -> espeak -> olaph -> crane` |    0.999 |          0.022 |                0.936 |
| `gold -> olaph -> espeak -> crane` |    0.999 |          0.921 |                0.936 |

These are quality measurements only. They do not change the implicit German selection,
which remains `("gold",)`.

## Artifact-size evidence

The current build and a HEAD baseline build were measured with the same build tool. The
baseline source tree was exported from HEAD and built with
`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_KOKOROG2P=0.0.0` because an archive has no VCS
metadata.

| Artifact | Baseline bytes | Current bytes |       Delta |
| -------- | -------------: | ------------: | ----------: |
| Wheel    |     19,035,677 |    34,628,472 | +15,592,795 |
| sdist    |     19,133,458 |    35,340,719 | +16,207,261 |

The current wheel contains the generated lexicons and notices. Canonical source files
are excluded from both release artifact types, as checked by
`scripts/check_release_artifacts.py`.

## Retained audits

- `lexicons/audits/de-de_espeak.json`
- `lexicons/audits/de-de_olaph.json`
- `lexicons/audits/de-de_espeak_inventory.json`
- `lexicons/audits/de-de_olaph_inventory.json`
