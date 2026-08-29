# KokoroG2P lexicons

`lexicons/sources` contains the canonical, human-editable pronunciation and membership data used to build the packaged G2Lex assets. The files in this directory are source material, not importable runtime resources.

`manifest.toml` defines each named lexicon, its source format, and generated package asset. `lock.json` records hashes and counts from the last deterministic build.

Regenerate all assets with:

```bash
python scripts/build_g2lex_assets.py --all
```

Check that a clean rebuild is byte-identical with:

```bash
python scripts/build_g2lex_assets.py --check
```

Validate source-to-asset equality without modifying files with:

```bash
python scripts/validate_g2lex_assets.py --all
```

Use `--id LANGUAGE:NAME` for a focused build or validation. Runtime code imports generated metadata from `kokorog2p/lexicons/_generated_registry.py`; it never parses this TOML file or reads `lexicons/sources`.

The first name in an explicit `lexicons=(...)` selection wins collisions. Missing `default_priority` means a lexicon is opt-in rather than part of the default stack. Third-party records must include a pinned revision, source URL, license expression/URL, and attribution before they can be shipped.
