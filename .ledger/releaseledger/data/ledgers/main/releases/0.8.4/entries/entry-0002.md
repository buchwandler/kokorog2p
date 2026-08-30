---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0002
release_version: 0.8.4
kind: changed
summary:
  Changed bundled language lexicons to lazy packaged G2Lex assets with named ordered
  selection
status: accepted
audience: null
scopes: []
source_refs:
  - git:654ca44016725cfd881f69be3381c329628a3eeb
paths:
  - .github/workflows/tests.yml
  - README.md
  - benchmarks/JAPANESE_DATASET.md
  - docs/advanced.md
  - docs/api/english.md
  - docs/api/french.md
  - docs/api/german.md
  - docs/api/japanese.md
  - docs/changelog.md
  - docs/installation.md
  - experiments/de_lexicon_compression/README.md
  - experiments/de_lexicon_entry_reduction/tests/test_entry_reduction.py
  - kokorog2p/__init__.py
  - kokorog2p/base.py
  - kokorog2p/de/g2p.py
  - kokorog2p/de/lexicon.py
  - kokorog2p/en/g2p.py
  - kokorog2p/en/lexicon.py
  - kokorog2p/fr/g2p.py
  - kokorog2p/fr/lexicon.py
  - kokorog2p/ja/cutlet.py
  - kokorog2p/ja/g2p.py
  - kokorog2p/lexicons/__init__.py
  - kokorog2p/lexicons/data/.de_gold.n8k5jsr8/de_gold.g2lex
  - kokorog2p/lexicons/data/__init__.py
  - kokorog2p/lexicons/data/de_gold.g2lex
  - kokorog2p/lexicons/data/en_gb_gold.g2lex
  - kokorog2p/lexicons/data/en_gb_silver.g2lex
  - kokorog2p/lexicons/data/en_us_gold.g2lex
  - kokorog2p/lexicons/data/en_us_silver.g2lex
  - kokorog2p/lexicons/data/fr_gold.g2lex
  - kokorog2p/lexicons/data/ja_words.g2lex
  - kokorog2p/lexicons/registry.py
  - kokorog2p/lexicons/runtime.py
  - kokorog2p/pipeline_api.py
  - lexicons/README.md
  - lexicons/lock.json
  - lexicons/manifest.toml
  - lexicons/sources/de/de_gold.json
  - lexicons/sources/en/gb_gold.json
  - lexicons/sources/en/gb_silver.json
  - lexicons/sources/en/us_gold.json
  - lexicons/sources/en/us_silver.json
  - lexicons/sources/fr/fr_gold.json
  - lexicons/sources/ja/ja_words.txt
  - pyproject.toml
  - scripts/build_g2lex_assets.py
  - scripts/check_release_artifacts.py
  - scripts/rebuild_lexicon_de.py
  - scripts/rebuild_lexicon_en_gb.py
  - scripts/rebuild_lexicon_en_us.py
  - scripts/rebuild_lexicon_fr.py
  - scripts/validate_g2lex_assets.py
  - tests/test_de_normalizer.py
  - tests/test_en_lexicon.py
  - tests/test_g2lex_assets.py
  - tests/test_g2lex_runtime_lifetime.py
  - tests/test_ja_g2p.py
  - tests/test_legacy_lexicon_parity.py
  - tests/test_lexicon_registry.py
  - tests/test_lexicon_selection.py
issues: []
prs: []
sources:
  - git:654ca44016725cfd881f69be3381c329628a3eeb
contributors: []
breaking: false
internal: false
order: 2
---
