---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0003
release_version: 0.9.4
kind: fixed
summary: Fixed eSpeak marker normalization and German phoneme conversion edge cases
status: accepted
audience: null
scopes: []
source_refs:
  - git:c4cb05ce394074de4b660159a07b5fa31d315f38
paths:
  - kokorog2p/backends/espeak/backend.py
  - kokorog2p/de/g2p.py
  - kokorog2p/phonemes.py
  - tests/test_de_g2p.py
  - tests/test_espeak_backend.py
  - tests/test_phonemes.py
issues: []
prs: []
sources:
  - git:c4cb05ce394074de4b660159a07b5fa31d315f38
contributors: []
breaking: false
internal: false
order: 3
---
