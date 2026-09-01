---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0019
release_version: 0.8.4
kind: changed
summary: Changed German Crane runtime keys to NFC lowercase with POS-aware collision
  resolution
status: accepted
audience: null
scopes: []
source_refs:
- git:63b7be365c204da76539a9482ea8bb03178db3f8
- git:9e2e871a5795e1092bcca0a6dae28eda220dc645
paths:
- docs/advanced.md
- docs/api/german.md
- kokorog2p/de/lexicon.py
- kokorog2p/lexicons/_generated_registry.py
- kokorog2p/lexicons/runtime.py
- lexicons/README.md
- lexicons/lock.json
- lexicons/manifest.toml
- pyproject.toml
- scripts/audit_lexicon_phoneme_inventory.py
- scripts/build_g2lex_assets.py
- scripts/de_crane_transform.py
- scripts/validate_g2lex_assets.py
- tests/test_de_crane_transform.py
- tests/test_de_g2p.py
- tests/test_g2lex_assets.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 19
---
