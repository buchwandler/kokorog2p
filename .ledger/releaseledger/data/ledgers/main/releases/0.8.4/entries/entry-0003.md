---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0003
release_version: 0.8.4
kind: changed
summary: Added strict ARPABET conversion and manifest-driven lexicon selection
status: accepted
audience: null
scopes: []
source_refs:
  - git:b7d457a1974b41c36bcd760e8e3086c4532f7631
paths:
  - .github/workflows/tests.yml
  - README.md
  - kokorog2p/__init__.py
  - kokorog2p/de/lexicon.py
  - kokorog2p/en/arpabet.py
  - kokorog2p/en/lexicon.py
  - kokorog2p/fr/lexicon.py
  - kokorog2p/lexicons/_generated_registry.py
  - kokorog2p/lexicons/data/.de_gold.n8k5jsr8/de_gold.g2lex
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
  - scripts/build_g2lex_assets.py
  - scripts/check_release_artifacts.py
  - scripts/validate_g2lex_assets.py
  - tests/test_cmudict_lexicon.py
  - tests/test_en_arpabet.py
  - tests/test_g2lex_assets.py
  - tests/test_legacy_lexicon_parity.py
  - tests/test_lexicon_manifest_generation.py
  - tests/test_lexicon_precedence.py
issues: []
prs: []
sources:
  - git:b7d457a1974b41c36bcd760e8e3086c4532f7631
contributors: []
breaking: false
internal: false
order: 3
---
