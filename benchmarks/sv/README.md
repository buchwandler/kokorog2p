# Swedish rule benchmark

`benchmark_sv_rules.py` evaluates the native Swedish rule engine against a local,
external reference TSV. The corpus is development data only and is never loaded by
`kokorog2p` at runtime.

## Usage

```bash
python benchmarks/benchmark_sv_rules.py \
  --lexicon /path/to/lexicon.tsv \
  --inspect-format 5000

python benchmarks/benchmark_sv_rules.py \
  --lexicon /path/to/lexicon.tsv \
  --split dev \
  --trace-failures \
  --output benchmarks/results/sv/dev
```

`--lexicon` may be replaced by `KOKOROG2P_SV_LEXICON`. The tool does not search implicit
home-directory paths and does not download the file. Use `--verify-sha256` to verify the
reviewed source hash.

Results include exact, stressless, quantity-insensitive, and phone error metrics, plus
TSV reports for failures, feature groups, confusions, rule coverage, stress, quantity,
affixes, n-grams, and baseline regressions.
