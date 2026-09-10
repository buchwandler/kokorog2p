---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0008
release_version: 0.9.4
kind: fixed
summary:
  Fixed Lexphon download handling, eSpeak error reporting, and test resource cleanup
status: accepted
audience: null
scopes: []
source_refs:
  - git:c340efa452e6ab35a956c84f5b3ee377898a7ded
paths:
  - .github/workflows/tests.yml
  - kokorog2p/backends/espeak/api.py
  - tests/conftest.py
  - tests/test_pipeline_api.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 8
---
