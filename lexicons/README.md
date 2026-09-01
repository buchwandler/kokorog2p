# KokoroG2P lexicons

`lexicons/sources` contains the canonical, human-editable pronunciation and membership
data used to build the packaged G2Lex assets. The files in this directory are source
material, not importable runtime resources.

`manifest.toml` defines each named lexicon, its source format, and generated package
asset. `lock.json` records hashes and counts from the last deterministic build.

The German Crane record is a build-time derivative. Its canonical TSV remains
byte-identical for provenance, while the packaged runtime asset normalizes keys to NFC
lowercase. Ambiguous case collisions can receive POS selectors from a pinned LexHint
German artifact. The `die` entry uses `DEFAULT`, `DET`, and `PRON`, all `diː`, so
sentence-initial capitalization cannot select the unrelated technical noun
pronunciation. LexHint is not a KokoroG2P runtime dependency; raw TSV logical parity is
not expected for transformed Crane assets.

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

The German `de-de:crane`, `de-de:espeak`, and `de-de:olaph` records intentionally omit
`default_priority`, so they are discoverable but never included in the implicit default
selection. Their canonical sources are revision-pinned and include SHA-256 and byte-size
metadata. See `sources/de/PROVENANCE.md` for source syntax, attribution, licensing, and
the no-network runtime policy.

The CSTR dictionaries use the `ipa-tsv` source adapter. It strips one outer `/.../`
delimiter pair, skips only the exact eSpeak header on physical row one, preserves
internal slashes, and preserves source order. OLaPh's two optional POS annotation rows
are imported as ordinary pronunciations because the runtime lexicon is not
role-specific.

Fetch or verify the pinned maintainer sources with:

```bash
python scripts/fetch_cstr_de_lexicons.py --all --check
python scripts/audit_cstr_de_sources.py --id de-de:espeak --id de-de:olaph
```

Third-party records identified by `provider` must provide `provider`, `revision`,
`source_url`, `license_expression`, `license_url`, and `attribution`. Build validation
checks these fields, source integrity, lossless packing, and lock metadata.
