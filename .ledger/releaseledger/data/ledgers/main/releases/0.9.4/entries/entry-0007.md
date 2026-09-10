---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0007
release_version: 0.9.4
kind: changed
summary:
  Changed English and French dictionary ownership to externally provisioned Lexphon data
status: accepted
audience: null
scopes: []
source_refs:
  - git:548ac11ab15eecdff78610ff6dac02e7a404f9a2
paths:
  - MANIFEST.in
  - README.md
  - docs/advanced.md
  - docs/api/core.md
  - docs/lexicons.md
  - kokorog2p/__init__.py
  - kokorog2p/en/lexicon.py
  - kokorog2p/fr/lexicon.py
  - kokorog2p/lexicons/registry.py
  - kokorog2p/lexicons/runtime.py
  - pyproject.toml
  - scripts/check_release_artifacts.py
  - tests/test_external_g2lex_runtime.py
  - tests/test_lexicon_registry.py
  - tests/test_lexicon_selection.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 7
---
