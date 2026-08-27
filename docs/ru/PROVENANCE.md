# Russian frontend provenance

## Clean-room statement

Russian support in KokoroG2P is an independent implementation. The file
`zaakirio/kokoro-ru/ru_g2p.py` at commit `6c10ac3c058d2baf887f8991049b845ce30b984b` is
used only as a behavioral oracle. KokoroG2P does not copy or vendor its implementation
source, comments, regular expressions, exception sets, generated tables, model weights,
compiled eSpeak data, or control flow. Any differential benchmark communicates with an
explicitly supplied oracle through process I/O only.

## Model and vocabulary

The Russian frontend targets the stock Kokoro 1.0 vocabulary. Russian does not introduce
token IDs or mutate the shared vocabulary. The implementation checks that every final
symbol is present in that profile before creating a `GToken`. The external `kokoro-ru`
weights are not a KokoroG2P dependency and are not bundled.

## Independent linguistic sources

The initial rules are deliberately conservative and are based on these independent
references:

- R. I. Avanesov, _Russian Literary Pronunciation and Stress_, Russian Language, 1984,
  for literary pronunciation, vowel reduction, and the pronunciation of `-ого/-его`.
- M. V. Panov, _Russian Phonetics_, Prosveshchenie, 1999, for positional vowel
  reduction, palatalized contexts, consonant clusters, and the limited lexical nature of
  `чн` variation.
- A. N. Gvozdev, _Modern Russian Literary Pronunciation_, 1967, for orthoepic exceptions
  and standard consonant cluster treatment.
- The Russian National Corpus and the Gramota.ru orthoepic reference service are used as
  independent checks when selecting lexical examples. Corpus and dictionary data are not
  distributed with the package.
- eSpeak-ng's public documentation and local probe output are used only to identify the
  raw symbols emitted by the selected system installation. No eSpeak dictionary or
  compiled data is copied into this project.

The implementation documents a source note next to each lexical rule family. A mismatch
with the behavioral oracle is not by itself evidence that a local rule is wrong.

## RUAccent

RUAccent is an optional runtime dependency. The selected package and model revision must
be recorded separately when an integration environment is chosen. No model is imported,
downloaded, or loaded during `import kokorog2p` or `import kokorog2p.ru`. The final
dependency bounds must reflect the tested Python and Transformers/ONNX Runtime
combination rather than an unverified latest-version assumption.

Current package metadata and model artifact terms must be checked at release time. This
document intentionally does not make a blanket license claim for future RUAccent model
artifacts.

## eSpeak-ng

eSpeak-ng source and language rule data are GPL-3.0-or-later. KokoroG2P uses a system or
separately installed eSpeak data path and verifies its behavior at runtime. The
reference repository's compiled `espeak-data` is not distributed here. If a custom
compiled data artifact is ever distributed, it requires a separate licensing review and
the appropriate GPL notices.

## Benchmark boundary

`benchmarks/benchmark_ru_differential.py` is diagnostic, not a source of implementation
data. It requires the caller to provide an oracle interpreter or command explicitly,
records only input/output behavior and metrics, and classifies mismatches as
implementation bugs, oracle bugs, valid variants, eSpeak differences, accentuator
differences, or unresolved cases.
