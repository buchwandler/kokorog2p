# Thai frontend provenance

## Clean-room statement

The Thai frontend is an independent implementation for `kokorog2p`. The pinned Wayu
repository is used only as an externally observed behavioral oracle. No Wayu
implementation source, comments, regular expressions, control flow, model weights,
generated name tables, evaluation corpus, or serving code is copied or vendored.

## Behavioral baseline

- Reference: `kunato/wayu-kokoro-thai-v1`
- Behavioral baseline commit: `50d7f60e41ac118e5bb92b0ba52c30bb7830103c`
- Later tree commits may be used only for packaging context, not as the behavioral
  baseline.
- Target vocabulary fact: Wayu uses `˩` (`U+02E9 MODIFIER LETTER EXTRA-LOW TONE BAR`) at
  token ID `7`.

## Dependencies and licenses

- Lexphon provides the provisioned `th:lexhint` pronunciation dictionary. The asset is
  installed and verified outside this package and is not downloaded at runtime.
- The Wayu model repository is Apache-2.0 licensed. This implementation does not
  redistribute its weights or source.

## Deliberate deviations

- Latin runs use the existing `kokorog2p.en.EnglishG2P` lazily instead of a direct
  Misaki English dependency.
- No external Thai runtime engine or generated Thai-name respelling database is
  included.
- No generated Thai-name respelling database, license-plate acrophony, or model-training
  entity patch table is included.
- Thai semantic normalization remains local to this package until a released
  `spokenform` version advertises the required Thai semantics.

## Fixture policy

Tests and benchmark cases are independently authored synthetic or reviewed cases.
Expected Thai pronunciation may be recorded from the released LexHint data, the observed
reference, or human review. Reference checkouts and network access are development-only
inputs and are not runtime or normal CI dependencies.
