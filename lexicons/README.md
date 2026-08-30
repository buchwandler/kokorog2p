# KokoroG2P lexicons

`lexicons/sources` contains the canonical, human-editable pronunciation and membership
data used to build the packaged G2Lex assets. The files in this directory are source
material, not importable runtime resources.

`manifest.toml` defines each named lexicon, its source format, and generated package
asset. `lock.json` records hashes and counts from the last deterministic build.

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

Use `--id LANGUAGE:NAME` for a focused build or validation. Runtime code imports
generated metadata from `kokorog2p/lexicons/_generated_registry.py`; it never parses
this TOML file or reads `lexicons/sources`.

The first name in an explicit `lexicons=(...)` selection wins collisions. Missing
`default_priority` means a lexicon is opt-in rather than part of the default stack.
Third-party records must include a pinned revision, source URL, license expression/URL,
and attribution before they can be shipped.

## Third-party sources

The German `de-de:crane` record is intentionally missing `default_priority`, so it is
discoverable but never included in an implicit default selection. Its canonical source
is the revision-pinned `de/de.tsv` file from `crane-local-ai/g2p-lexicons`; the manifest
also pins its SHA-256 and byte size. Keep the source unchanged: case policy belongs to
the German consumer, while repeated TSV rows remain ordered pronunciation variants.

Third-party records identified by `provider` or `third_party = true` must provide
`provider`, `revision`, `source_url`, `license_expression`, `license_url`, and
`attribution`. Build validation checks these fields, source integrity, lossless packing,
and lock metadata. The generated Crane asset is CC BY-SA 4.0 data derived from German
Wiktionary; see `sources/de/PROVENANCE.md` and the bundled runtime notice.
