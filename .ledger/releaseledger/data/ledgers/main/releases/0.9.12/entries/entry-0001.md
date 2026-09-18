---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.9.12
kind: changed
summary:
  Changed eSpeak runtime diagnostics, cache cleanup, and batch phonemization support
status: accepted
audience: null
scopes: []
source_refs:
  - git:9ce1dabd70fdf3957e83655ca91d6d61c682c556
paths:
  - README.md
  - kokorog2p/__init__.py
  - kokorog2p/backends/espeak/backend.py
  - kokorog2p/espeak_g2p.py
  - pyproject.toml
  - tests/test_dependency_contract.py
  - tests/test_espeak_backend.py
  - tests/test_espeak_batching.py
issues: []
prs: []
sources:
  - git:9ce1dabd70fdf3957e83655ca91d6d61c682c556
contributors:
  - "@holgern"
breaking: false
internal: false
order: 1
---
