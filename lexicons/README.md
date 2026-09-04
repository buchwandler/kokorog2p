# KokoroG2P lexicons

This directory contains the build inputs for the packaged lexicons still owned by
KokoroG2P. `manifest.toml` defines those records and `lock.json` records hashes and
counts from the last deterministic build.

German pronunciation data is not a KokoroG2P build input. German datasets are produced
and published by `g2lex-data`, then installed explicitly into Lexphon's local data
store. KokoroG2P only maps its public German names to the external Lexphon IDs and
consumes them at runtime. It does not download, generate, audit, or package German
dictionaries.

Regenerate remaining packaged assets with:

```bash
python scripts/build_g2lex_assets.py --all
```

Check that a clean rebuild is byte-identical with:

```bash
python scripts/build_g2lex_assets.py --check
```

Validate remaining source-to-asset equality without modifying files with:

```bash
python scripts/validate_g2lex_assets.py --all
```

Runtime code imports generated metadata from
`kokorog2p/lexicons/_generated_registry.py`; it never parses this TOML file or reads
canonical source files. The first name in an explicit selection wins collisions. Missing
`default_priority` means a packaged lexicon is opt-in rather than part of a default
stack. Third-party packaged records must include pinned provenance and licensing
metadata.
