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
