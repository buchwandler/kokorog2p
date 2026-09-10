# German synthetic benchmark dataset

German benchmark data uses externally provisioned Lexphon dictionaries. KokoroG2P does
not ship or build German dictionary assets.

```bash
lexphon data install de-de:gold de-de:crane de-de:espeak de-de:olaph de-de:lexhint
lexphon data verify de-de:gold de-de:crane de-de:espeak de-de:olaph de-de:lexhint
```

Use `GermanG2P(lexicons=("gold",))` for the default dictionary profile, an ordered tuple
for layered comparisons, and `lexicons=()` for fallback-only measurements. The synthetic
`de_synthetic.json` dataset can be consumed by a local benchmark harness after
provisioning.

Validate its structure with:

```bash
python benchmarks/validate_synthetic_data.py benchmarks/data/de_synthetic.json
```
