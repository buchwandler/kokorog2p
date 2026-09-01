---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0018
release_version: 0.8.4
kind: fixed
summary: Fixed German currency preparation to retain minor-unit wording in spoken output
status: accepted
audience: null
scopes: []
source_refs:
  - git:f644076b76bb3f7e5c2d73f3377a61e1748846cf
  - git:93e1f648ea9d38365136da38e401ae08fc9b64ff
  - git:465ca5a9748515692e4b84c4c7596f5bdf3eda3f
paths:
  - kokorog2p/pipeline_api.py
  - tests/data/de_semantic_parity.json
  - tests/test_de_normalizer.py
  - tests/test_dependency_contract.py
  - tests/test_pipeline_api.py
  - tests/test_spokenform_migration.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 18
---
