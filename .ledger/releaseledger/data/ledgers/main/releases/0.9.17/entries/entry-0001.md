---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: 0.9.17
kind: fixed
summary: Normalize Lexphon/eSpeak U+200D ties before Kokoro conversion
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0115
paths:
  - kokorog2p/phonemes.py
  - docs/phonemes.md
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 1
---

Canonicalize zero-width joiners before English diphthong and affricate mappings, fixing
OOV provider pronunciations such as failsafe and preventing U+200D from reaching
model-ID generation.
