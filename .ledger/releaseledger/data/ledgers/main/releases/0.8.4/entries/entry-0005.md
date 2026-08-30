---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0005
release_version: 0.8.4
kind: changed
summary:
  Changed German IPA handling to reject invalid pronunciations and preserve fallback
status: accepted
audience: null
scopes: []
source_refs:
  - git:28f8b4250711cc816f0e5e293b922aa790fe2642
paths:
  - .github/workflows/tests.yml
  - MANIFEST.in
  - docs/index.md
  - docs/lexicons.md
  - kokorog2p/__init__.py
  - kokorog2p/de/g2p.py
  - kokorog2p/de/lexicon.py
  - kokorog2p/lexicons/runtime.py
  - lexicons/lock.json
  - pyproject.toml
  - scripts/audit_lexicon_phoneme_inventory.py
  - scripts/check_release_artifacts.py
  - tests/test_de_g2p.py
  - tests/test_de_g2p_hardening.py
  - tests/test_dependency_contract.py
  - tests/test_lexicon_precedence.py
  - tests/test_lexicon_selection.py
  - tests/test_release_artifacts.py
issues: []
prs: []
sources:
  - git:28f8b4250711cc816f0e5e293b922aa790fe2642
contributors: []
breaking: false
internal: false
order: 5
---
