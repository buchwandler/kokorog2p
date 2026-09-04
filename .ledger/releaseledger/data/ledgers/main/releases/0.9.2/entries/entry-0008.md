---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0008
release_version: 0.9.2
kind: quality
summary:
  Added deterministic multi-language station benchmarks with scaled workloads and
  aggregate diagnostics
status: accepted
audience: null
scopes: []
source_refs: []
paths:
  - .github/workflows/tests.yml
  - benchmarks/benchmark_all_stations.py
  - benchmarks/benchmark_language_stations.py
  - benchmarks/station_corpora.py
  - tests/test_station_benchmarks.py
issues: []
prs: []
sources:
  - git:73cc7193115aeeda6aca2b993dce518708c317fa
contributors: []
breaking: false
internal: false
order: 8
---
