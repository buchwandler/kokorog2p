---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0004
release_version: 0.9.4
kind: changed
summary:
  Changed native frontend fallback execution to use shared Lexphon 0.2 providers and
  standardized provider metadata
status: accepted
audience: null
scopes: []
source_refs:
  - git:9f9ccbf7217dd04e237182c1762348e3e25dc393
paths:
  - README.md
  - benchmarks/benchmark_g2p.py
  - benchmarks/generate_phonemes.py
  - docs/advanced.md
  - docs/api/french.md
  - docs/api/swedish.md
  - docs/api/utils.md
  - docs/api/vietnamese.md
  - kokorog2p/__init__.py
  - kokorog2p/base.py
  - kokorog2p/cs/fallback.py
  - kokorog2p/cs/g2p.py
  - kokorog2p/de/fallback.py
  - kokorog2p/de/g2p.py
  - kokorog2p/de/lexicon.py
  - kokorog2p/de/lexphon_backend.py
  - kokorog2p/en/fallback.py
  - kokorog2p/en/g2p.py
  - kokorog2p/fallback_base.py
  - kokorog2p/fr/fallback.py
  - kokorog2p/fr/g2p.py
  - kokorog2p/language_pairs/__init__.py
  - kokorog2p/language_pairs/registry.py
  - kokorog2p/language_routing.py
  - kokorog2p/lexicons/evidence.py
  - kokorog2p/lexicons/lexphon_backend.py
  - kokorog2p/sv/g2p.py
  - kokorog2p/vi/g2p.py
  - pyproject.toml
  - scripts/rebuild_lexicon_en_gb.py
  - scripts/rebuild_lexicon_en_us.py
  - scripts/rebuild_lexicon_fr.py
  - tests/test_base.py
  - tests/test_ci_bug_fix.py
  - tests/test_de_g2p.py
  - tests/test_de_g2p_hardening.py
  - tests/test_de_gold_performance.py
  - tests/test_dependency_contract.py
  - tests/test_en_g2p.py
  - tests/test_fr_g2p.py
  - tests/test_ja_g2p.py
  - tests/test_lexhint_adoption.py
  - tests/test_lexicon_evidence.py
  - tests/test_lexphon_backend.py
  - tests/test_ru_g2p.py
  - tests/test_semantic_ownership.py
  - tests/test_sv_g2p.py
  - tests/test_th_g2p.py
  - tests/test_th_prepared_input.py
issues: []
prs: []
sources:
  - git:9f9ccbf7217dd04e237182c1762348e3e25dc393
contributors: []
breaking: false
internal: false
order: 4
---
