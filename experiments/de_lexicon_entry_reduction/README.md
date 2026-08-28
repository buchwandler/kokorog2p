# German resident lexicon entry reduction

This directory contains the isolated V1 and V2 research experiment for replacing
resident German pronunciation literals with a smaller reusable basis and deterministic
runtime composition.

## Contract

- The builder may use canonical IPA offline to decide whether omission is exact.
- Runtime lookup uses only the queried spelling, literal entries, shared indexes,
  membership, and compact global rules.
- Exact membership, pronunciation tuples, variant count, and variant order are
  preserved.
- Generated words do not have serialized recipes, split maps, IDs, or exception tables.
- Production German files and task-0039 artifacts are not modified.
- The pinned baseline contains 738,427 words. The primary V2 target is at most 400,000
  literals.

## V1 reproduction

```bash
python experiments/de_lexicon_entry_reduction/run.py \
  --source builtin --mode implicit-compound --optimizer greedy \
  --output experiments/de_lexicon_entry_reduction/reports/v1-reproduction
```

The frozen V1 result is 586,889 literals, 151,538 generated words, zero recipes, and
exact reload verification for all 738,427 words.

## V2 stages

The opt-in flags are independently switchable:

```bash
python experiments/de_lexicon_entry_reduction/run.py \
  --source builtin --mode implicit-compound --optimizer greedy \
  --selector v2 --boundary-rules v2 --linkers german \
  --recursive-components --max-components 6 --max-states 100000 \
  --output experiments/de_lexicon_entry_reduction/reports/v2-best
```

Available mechanisms are the compact rule selector, measured boundary rules, German
linkers, recursive proper-substring resolution, utility basis promotion, an integer
segmentation scorer, and a bounded shared affix grammar. Each mechanism is oracle-free
at runtime and is admitted only through an exact rebuild and reload check.

Run the staged matrix with:

```bash
python experiments/de_lexicon_entry_reduction/run_matrix.py \
  --source builtin --v2-stages \
  --output experiments/de_lexicon_entry_reduction/reports/matrix
```

The ordinary matrix mode remains available for bounded V1 comparisons.

## Offline diagnostics

Diagnostics may read expected IPA. They are never loaded by the candidate runtime.

```bash
python experiments/de_lexicon_entry_reduction/analyze_failures.py \
  --source builtin \
  --run experiments/de_lexicon_entry_reduction/reports/v1-reproduction \
  --top-k-segmentations 16 --boundary-window 3 \
  --output experiments/de_lexicon_entry_reduction/reports/v2-diagnostics
```

The output contains retained-word groups, alternate-rule counts, top-K segmentation
counts, boundary edit families, and linker opportunity metrics.

## Verification and benchmarks

```bash
python experiments/de_lexicon_entry_reduction/verify.py \
  --source builtin --run experiments/de_lexicon_entry_reduction/reports/v2-best
python experiments/de_lexicon_entry_reduction/benchmark_memory.py \
  --source builtin --run experiments/de_lexicon_entry_reduction/reports/v2-best
python -m pytest -q experiments/de_lexicon_entry_reduction/tests
```

Full built-in matrix and memory work is intentionally opt-in because it requires
substantial RAM and CPU time. A target failure is reported numerically rather than
redefined.
