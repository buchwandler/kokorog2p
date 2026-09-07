---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0004
release_version: 0.9.3
kind: fixed
summary:
  Fixed benchmark-found pronunciation and routing edge cases across Japanese, Kazakh,
  Russian, and Vietnamese frontends
status: accepted
audience: null
scopes: []
source_refs:
  - git:352089fa68ea66d0d4a8cc62a3fb1d780ad3dcd2
paths:
  - kokorog2p/ja/g2p.py
  - kokorog2p/kk/model_profile.py
  - kokorog2p/language_routing.py
  - kokorog2p/lexicons/evidence.py
  - kokorog2p/ru/g2p.py
  - kokorog2p/vi/g2p.py
  - tests/test_ja_g2p.py
  - tests/test_lexhint_released_integration.py
  - tests/test_ru_g2p.py
  - tests/test_vi_g2p.py
issues: []
prs: []
sources:
  - git:352089fa68ea66d0d4a8cc62a3fb1d780ad3dcd2
contributors: []
breaking: false
internal: false
order: 4
---
