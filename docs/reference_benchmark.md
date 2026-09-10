# Reference benchmark

The reference benchmark checks the reviewed KokoroG2P compatibility corpus for the
pinned English US, English GB, and German reference profiles.

## Quick golden health check

Use the committed goldens for routine checks. This path does not import or execute
Misaki:

```bash
python benchmarks/benchmark_reference.py --quick --suite core
```

For one profile, use `--reference-source golden` explicitly:

```bash
python benchmarks/benchmark_reference.py \
  --reference hexgrad-en-us-v1 \
  --candidate en-us-default \
  --reference-source golden \
  --format summary \
  --fail-on regression
```

The process codes are `0` for PASS, `1` for a candidate or policy failure, and `2` for
invalid benchmark or reference infrastructure configuration.

## Detailed output

Use `--format json` for one complete machine-readable document or `--format markdown`
for decision-oriented diagnostics. `--json` and `--markdown` remain compatibility
aliases.

```bash
python benchmarks/benchmark_reference.py \
  --reference hexgrad-en-us-v1 \
  --candidate en-us-default \
  --reference-source golden \
  --format markdown \
  --sample-limit 20
```

`--json-output` and `--markdown-output` can be supplied together. The benchmark executes
once and renders both artifacts from the same report. `--only-differences`,
`--show-matches`, and `--baseline` modify that report instead of appending a second
document to stdout.

## Live verification

Live Misaki execution is explicit and is intended for reference verification or reviewed
golden refreshes:

```bash
python benchmarks/benchmark_reference.py \
  --reference hexgrad-en-us-v1 \
  --candidate en-us-default \
  --reference-source live \
  --verify-reference-golden benchmarks/reference/goldens/hexgrad_en_us_v1.json \
  --strict-reference
```

Live provider initialization is performed before candidate execution. Missing or invalid
Misaki infrastructure is reported as `ERROR` rather than as a successful comparison
containing only reference errors.

## Policies and schema

Corpus cases use `exact`, `normalized`, `model-id`, `model-valid`, or `diagnostic`
policies. Diagnostic pronunciation differences are visible but non-gating. Candidate
exceptions, invalid or lossy model encoding, public token-ID inconsistencies, and failed
gating policies fail the health check.

Serialized reports use schema version 2 and include the explicit verdict, source,
benchmark identity, execution metadata, aggregate policy counters, and detailed case
diagnostics.
