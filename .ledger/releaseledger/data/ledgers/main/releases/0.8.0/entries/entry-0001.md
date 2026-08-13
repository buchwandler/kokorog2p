---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 3
entry_id: entry-0001
release_version: 0.8.0
kind: changed
summary:
  Changed German area, volume, hectare, and speed quantities to use the shared
  spokenform grammar
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0018
paths: []
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 1
---

Direct German normalization and the public source-aligned span pipeline now share the
released extended-quantity behavior, including Unicode and ASCII square/cubic aliases
and source-offset handling.
