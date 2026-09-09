---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.9.4
kind: added
summary: Added German LexHint dictionary selection and explicit provisioning support
status: accepted
audience: null
scopes: []
source_refs:
  - git:221395a03c7bd6245098500689c4009abe978b1b
paths:
  - .github/workflows/tests.yml
  - .ledger/releaseledger/data/ledgers/main/events/events.jsonl
  - .ledger/releaseledger/data/ledgers/main/releases/0.9.4/release.md
  - docs/advanced.md
  - docs/installation.md
  - docs/lexicons.md
  - kokorog2p/de/lexphon_backend.py
  - kokorog2p/lexicons/registry.py
  - kokorog2p/tokenization.py
  - kokorog2p/types.py
  - tests/conftest.py
  - tests/test_de_lexphon_integration.py
  - tests/test_lexicon_registry.py
  - tests/test_pipeline_api.py
  - tests/test_prepared_core.py
issues: []
prs: []
sources:
  - git:221395a03c7bd6245098500689c4009abe978b1b
contributors: []
breaking: false
internal: false
order: 1
---
