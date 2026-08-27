# Russian benchmark input

The Russian differential benchmark accepts UTF-8 JSONL with one object per line:

```json
{"text": "Это пример."}
```

No Russian corpus or oracle package is bundled. Supply an external oracle worker
explicitly with `KOKOROG2P_RU_ORACLE_COMMAND`, or provide both
`KOKOROG2P_RU_ORACLE_PYTHON` and `KOKOROG2P_RU_ORACLE_MODULE`. The worker receives JSONL
objects on stdin and returns JSONL objects containing `phonemes` or `ipa`.

```bash
KOKOROG2P_RU_ORACLE_PYTHON=/path/to/oracle-venv/bin/python \
KOKOROG2P_RU_ORACLE_MODULE=oracle_worker \
python benchmarks/benchmark_ru_differential.py corpus.jsonl
```

Capability diagnostics are independent of the oracle:

```bash
python -m benchmarks.benchmark_ru_differential --probe-espeak
```

Results are diagnostic. Mismatches must be classified before becoming local regressions.
