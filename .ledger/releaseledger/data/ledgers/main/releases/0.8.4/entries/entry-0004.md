---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0004
release_version: 0.8.4
kind: added
summary:
  Added an opt-in German Crane/Wiktionary pronunciation lexicon with pinned provenance
  and named public selection
status: accepted
audience: null
scopes: []
source_refs:
  - git:66a935d2043beb6f9f0ed04f1488179146c56d80
paths:
  - .github/workflows/tests.yml
  - README.md
  - docs/advanced.md
  - docs/api/german.md
  - kokorog2p/__init__.py
  - kokorog2p/de/g2p.py
  - kokorog2p/de/lexicon.py
  - kokorog2p/lexicons/_generated_registry.py
  - kokorog2p/lexicons/data/THIRD_PARTY_NOTICES.md
  - kokorog2p/lexicons/data/de_crane.g2lex
  - kokorog2p/lexicons/data/de_gold.g2lex
  - kokorog2p/lexicons/data/en_gb_gold.g2lex
  - kokorog2p/lexicons/data/en_gb_silver.g2lex
  - kokorog2p/lexicons/data/en_us_gold.g2lex
  - kokorog2p/lexicons/data/en_us_silver.g2lex
  - kokorog2p/lexicons/data/fr_gold.g2lex
  - kokorog2p/lexicons/data/ja_words.g2lex
  - kokorog2p/lexicons/registry.py
  - kokorog2p/lexicons/runtime.py
  - lexicons/README.md
  - lexicons/lock.json
  - lexicons/manifest.toml
  - lexicons/sources/de/PROVENANCE.md
  - lexicons/sources/de/crane_wiktionary.tsv
  - pyproject.toml
  - scripts/audit_lexicon_phoneme_inventory.py
  - scripts/build_g2lex_assets.py
  - scripts/validate_g2lex_assets.py
  - tests/test_de_g2p.py
  - tests/test_dependency_contract.py
  - tests/test_g2lex_assets.py
  - tests/test_g2lex_runtime_lifetime.py
  - tests/test_lexicon_manifest_generation.py
  - tests/test_lexicon_precedence.py
  - tests/test_lexicon_registry.py
  - tests/test_lexicon_selection.py
issues: []
prs: []
sources:
  - git:66a935d2043beb6f9f0ed04f1488179146c56d80
contributors: []
breaking: false
internal: false
order: 4
---
