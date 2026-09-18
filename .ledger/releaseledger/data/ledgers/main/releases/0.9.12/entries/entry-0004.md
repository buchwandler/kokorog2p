---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0004
release_version: 0.9.12
kind: fixed
summary:
  Fixed English eSpeak fallback pronunciation and debug consistency while updating
  runtime dependency bounds
status: accepted
audience: null
scopes: []
source_refs:
  - git:bdce59723286c945f33a8045b3add484612ab255
paths:
  - kokorog2p/__init__.py
  - kokorog2p/en/g2p.py
  - pyproject.toml
  - tests/test_dependency_contract.py
  - tests/test_en_debug.py
  - tests/test_en_g2p.py
issues: []
prs: []
sources:
  - git:bdce59723286c945f33a8045b3add484612ab255
contributors:
  - "@holgern"
breaking: false
internal: false
order: 4
---
