---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0009
release_version: 0.8.4
kind: fixed
summary:
  Fixed shared packaged lexicon resources so closing one G2P instance does not
  invalidate active consumers
status: accepted
audience: null
scopes: []
source_refs:
  - git:d11d5500a42ee2f65c8629762a6aa81f6ffa1cd3
paths:
  - kokorog2p/lexicons/runtime.py
  - kokorog2p/lexicons/__init__.py
  - kokorog2p/__init__.py
  - kokorog2p/en/lexicon.py
  - kokorog2p/de/lexicon.py
  - kokorog2p/fr/lexicon.py
  - tests/test_g2lex_runtime_lifetime.py
  - tests/test_memory_regressions.py
issues: []
prs: []
sources:
  - git:d11d5500a42ee2f65c8629762a6aa81f6ffa1cd3
contributors: []
breaking: false
internal: false
order: 9
---
