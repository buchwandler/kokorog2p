---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0005
release_version: 0.9.4
kind: quality
summary:
  Improved mixed-language station benchmark coverage and completed shared Lexphon
  provider integration
status: accepted
audience: null
scopes: []
source_refs:
  - git:6ebdc3a89d608964e4b1b1b9958fb43b4574f04b
paths:
  - README.md
  - benchmarks/benchmark_g2p.py
  - benchmarks/benchmark_mixed_language_auto_stations.py
  - docs/advanced.md
  - docs/api/swedish.md
  - docs/api/utils.md
  - docs/api/vietnamese.md
  - kokorog2p/base.py
  - kokorog2p/de/g2p.py
  - kokorog2p/de/lexicon.py
  - kokorog2p/en/g2p.py
  - kokorog2p/fr/g2p.py
  - kokorog2p/language_pairs/de_en.py
  - kokorog2p/lexicons/lexphon_backend.py
  - kokorog2p/pipeline_api.py
  - pyproject.toml
  - tests/test_base.py
  - tests/test_de_g2p.py
  - tests/test_de_g2p_hardening.py
  - tests/test_de_gold_performance.py
  - tests/test_dependency_contract.py
  - tests/test_en_g2p.py
  - tests/test_fr_g2p.py
  - tests/test_lexicon_evidence.py
  - tests/test_lexphon_backend.py
  - tests/test_pipeline_api.py
  - tests/test_station_benchmarks.py
issues: []
prs: []
sources:
  - git:6ebdc3a89d608964e4b1b1b9958fb43b4574f04b
contributors: []
breaking: false
internal: false
order: 5
---
