---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0007
release_version: 0.9.5
kind: fixed
summary:
  Fixed cross-platform eSpeak voice selection and updated Thai provisioning to the
  native LexHint asset
status: accepted
audience: null
scopes: []
source_refs:
  - git:ab5c00d50e34bdc1fcbc6148178bbd6202fbfc89
paths:
  - kokorog2p/backends/espeak/cli_wrapper.py
  - kokorog2p/backends/espeak/phonemizer_base.py
  - kokorog2p/lexicons/registry.py
  - kokorog2p/th/g2p.py
  - docs/api/thai.md
  - docs/installation.md
  - docs/th/PROVENANCE.md
  - tests/test_espeak_backend.py
  - tests/test_lexicon_registry.py
  - tests/test_lexphon_backend.py
  - tests/test_th_g2p.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 7
---
