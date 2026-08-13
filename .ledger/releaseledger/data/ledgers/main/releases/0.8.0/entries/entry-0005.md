---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 3
entry_id: entry-0005
release_version: 0.8.0
kind: changed
summary:
  Changed migrated-language written-to-spoken semantics to use Spokenform 0.2.5 and
  raised the abbr2words floor to 0.2.7
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0022
paths:
  - pyproject.toml
  - kokorog2p/pipeline_api.py
  - kokorog2p/de/normalizer.py
  - kokorog2p/en/normalizer.py
  - tests/test_spokenform_migration.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 5
---

Removed downstream German currency and English cardinal compatibility rewrites so
kokorog2p preserves accepted Spokenform semantic replacements while retaining
typography, source alignment, and G2P behavior. Intentional outputs now follow the
upstream gold standard, including compact German currency and current English
numeric/date rendering.
