---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.9.16
kind: added
summary:
  Added context-aware English heteronym resolution and local G2Lex sources with
  traceable pronunciation provenance
status: accepted
audience: null
scopes: []
source_refs:
  - git:2623b8dd991ad5449f18e3f52101338897a3b3d0
paths:
  - kokorog2p/__init__.py
  - kokorog2p/en/g2p.py
  - kokorog2p/en/heteronyms.py
  - kokorog2p/en/lexicon.py
  - kokorog2p/lexicons/__init__.py
  - kokorog2p/lexicons/registry.py
  - kokorog2p/lexicons/runtime.py
  - kokorog2p/pipeline_api.py
  - kokorog2p/tokenization.py
  - tests/fixtures/english_heteronyms.json
  - tests/test_en_heteronyms.py
  - tests/test_local_g2lex_sources.py
  - tests/test_pipeline_api.py
issues: []
prs: []
sources:
  - git:2623b8dd991ad5449f18e3f52101338897a3b3d0
contributors:
  - "@holgern"
breaking: false
internal: false
order: 1
---
