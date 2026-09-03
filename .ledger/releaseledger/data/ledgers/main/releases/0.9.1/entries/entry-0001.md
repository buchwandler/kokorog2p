---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.9.1
kind: added
summary:
  Added an opt-in Swedish NST pronunciation lexicon and normalized German lexicon output
  before fallback processing
status: accepted
audience: null
scopes: []
source_refs:
  - git:a1f1e5db14b44d0952e401e212e96ea05c051496
paths:
  - docs/lexicons.md
  - kokorog2p/de/g2p.py
  - kokorog2p/lexicons/_generated_registry.py
  - kokorog2p/lexicons/data/THIRD_PARTY_NOTICES.md
  - kokorog2p/lexicons/data/sv_nst.g2lex
  - kokorog2p/lexicons/registry.py
  - lexicons/lock.json
  - lexicons/manifest.toml
  - lexicons/sources/sv/sv_nst.tsv
  - scripts/build_g2lex_assets.py
  - tests/test_de_g2p.py
  - tests/test_g2lex_assets.py
  - tests/test_lexicon_registry.py
  - tests/test_pipeline_api.py
issues: []
prs: []
sources:
  - git:a1f1e5db14b44d0952e401e212e96ea05c051496
contributors: []
breaking: false
internal: false
order: 1
---
