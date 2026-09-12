---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0002
release_version: 0.9.8
kind: fixed
summary:
  Fixed Russian LexHint tie-bar affricates by normalizing them to stock Kokoro labels
  before vocabulary validation
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0076
paths:
  - kokorog2p/ru/model_profile.py
  - tests/test_ru_model_profile.py
  - tests/test_ru_g2p.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 2
---
