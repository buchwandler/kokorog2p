# German lexicon provenance

These canonical sources are maintainer inputs used to generate packaged G2Lex assets.
Runtime lookup uses only the generated assets and performs no network access.

## Crane / Wiktionary

The `de-de:crane` source is the exact `de/de.tsv` file from
`crane-local-ai/g2p-lexicons` at revision `bfd51698069a30e1b20bbf54479b55af50b4161d`.

- Source file: `crane_wiktionary.tsv` (`de/de.tsv` upstream)
- Source URL:
  https://huggingface.co/datasets/crane-local-ai/g2p-lexicons/blob/bfd51698069a30e1b20bbf54479b55af50b4161d/de/de.tsv
- SHA-256: `04a3909f07cd08615157393814188b420a7c3c5035cf7a0608d31be07892be29`
- Size: 32,367,922 bytes
- Format: UTF-8 `word<TAB>ipa`; repeated rows preserve ordered accepted pronunciations
- Generated asset: `kokorog2p/lexicons/data/de_crane.g2lex`
- License: CC BY-SA 4.0
- Attribution: German Wiktionary contributors; dataset extraction and publishing by
  Crane Local AI

## CSTR eSpeak-derived dictionary

The `de-de:espeak` source is `espeak_de.tsv` from `cstr/g2p-dicts` at revision
`eeac6ffc9271838fd63464a83d4b784ac75fc95b`.

- Source URL:
  https://huggingface.co/datasets/cstr/g2p-dicts/blob/eeac6ffc9271838fd63464a83d4b784ac75fc95b/espeak_de.tsv
- SHA-256: `190b62f1ddcf6616b62214173f05b09804635b170f75b9877eceab20b1624dbf`
- Size: 23,829,981 bytes
- Format: UTF-8 `word<TAB>/IPA/`, with the first-row `word<TAB>espeak_ipa` header
- Import policy: the source adapter removes one outer slash delimiter pair, skips only
  that exact first-row header, and preserves internal slashes and ordered variants
- Generated asset: `kokorog2p/lexicons/data/de_espeak.g2lex`
- License: CC BY-SA 3.0 for the open-dict-data/Wiktionary-derived source vocabulary
- Attribution: German word inventory from open-dict-data/Wiktionary-derived data; IPA
  generated with eSpeak tooling and redistributed by cstr/g2p-dicts

## CSTR OLaPh dictionary

The `de-de:olaph` source is `olaph_de.txt` from `cstr/g2p-dicts` at revision
`cedb4ada41a288549db36c53f9a1e6858a668624`. The source contains two optional POS
annotations; the import adapter retains their pronunciations and ignores those
annotations because the runtime lexicon is not role-specific.

- Source URL:
  https://huggingface.co/datasets/cstr/g2p-dicts/blob/cedb4ada41a288549db36c53f9a1e6858a668624/olaph_de.txt
- SHA-256: `aa70d85ce245c8a8f1db2cc109a0f3da6594eaba5b414a61bcd28f1ccc40ca46`
- Size: 41,709,849 bytes
- Format: UTF-8 `word<TAB>/IPA/` with optional source annotation field
- Import policy: the source adapter removes one outer slash delimiter pair and preserves
  internal slashes and ordered variants
- Generated asset: `kokorog2p/lexicons/data/de_olaph.g2lex`
- License: MIT
- Attribution: OLaPh (Optimal Language Phonemizer), IISYS Hof; source redistributed by
  cstr/g2p-dicts

The strict German consumer converts source IPA to the Kokoro target vocabulary. It
rejects unsupported material rather than silently deleting it, allowing configured
fallbacks to handle unusable pronunciations. Neither source is part of the implicit
German default stack, and neither source is downloaded at runtime.
