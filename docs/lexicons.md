# Lexicon assets and release policy

KokoroG2P keeps canonical lexicon sources outside the importable package. Runtime code
opens only generated `.g2lex` resources through `importlib.resources`; it never
downloads or reads canonical source files.

## German Crane consumer contract

The Crane asset stores source-ordered IPA variants losslessly. The German consumer
selects the first source-ordered pronunciation and applies this explicit target-profile
conversion:

| Source sequence/class                                                     | Target representation  | Decision                                       |
| ------------------------------------------------------------------------- | ---------------------- | ---------------------------------------------- |
| `t͡s`, `t͡ʃ`, `d͡ʒ`, `d͡z`, `ts`, `dz`                                        | `ʦ`, `ʧ`, `ʤ`, `ʣ`     | Explicit affricate mapping                     |
| `aɪ`, `aʊ`, `ɔʏ`                                                          | `I`, `W`, `ɔy`         | Kokoro German benchmark/profile tokens         |
| `ʏ` and listed foreign IPA approximations                                 | Explicit target symbol | Mapped only where the table defines it         |
| `̯`, `̩`                                                                    | no output              | Explicitly ignored non-syllabic/syllabic marks |
| transcription delimiters, articulatory detail, joining and prosodic marks | no output              | Explicitly ignored non-semantic consumer marks |
| anything else                                                             | preserved and rejected | Unhandled material; release audit fails        |

NFC normalization is applied before classification. Normalization results retain mapped,
ignored, and unsupported classifications so an audit cannot pass merely because
unsupported characters were filtered away. An invalid or empty first pronunciation is a
failed dictionary result and cannot suppress fallback.

The production profile intentionally uses `I`/`W` for German diphthongs, matching the
pinned Crane benchmark normalizer and the target Kokoro token profile. Raw
`GermanLexicon.lookup()` values remain the original source IPA (for example, `haʊ̯`);
conversion occurs at the German G2P consumer boundary.

## Distribution policy

The wheel contains generated `.g2lex` assets and
`kokorog2p/lexicons/data/THIRD_PARTY_NOTICES.md`, but not canonical source data. The
source distribution follows the same generated-asset-centric policy: `lexicons/sources/`
is deliberately excluded, including the large Crane TSV. Provenance and license notices
remain included so the redistributed compiled asset remains identified as CC BY-SA 4.0
data derived from German Wiktionary. The Crane data is not Apache-licensed merely
because the surrounding code is Apache-2.0.
