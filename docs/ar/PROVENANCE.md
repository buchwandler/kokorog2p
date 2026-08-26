# Arabic clean-room provenance

- Review date: 2026-08-26
- Target: Modern Standard Arabic (MSA)
- Model profile: `nabra-82m-v0.1`

The Arabic frontend is an independent implementation based on the behavior and
interoperability requirements in `01_todo.md`, KokoroG2P's public architecture,
and public eSpeak-ng and CAMeL Tools APIs. No source from the external Arabic
reference was copied, translated, mechanically rewritten, or vendored.

## Behavioral sources

- Oddadmix reference revision: [raw revision](https://gist.githubusercontent.com/Oddadmix/dc699f7942a9516ce29d4842c7aed756/raw/827b541c892a862f9ef3b44006a6e27b100d1bdd/arabic_g2p.py)
- Nabra model card: [oddadmix/Nabra-82M-v0.1](https://huggingface.co/oddadmix/Nabra-82M-v0.1)
- CAMeL Tools API: [documentation](https://camel-tools.readthedocs.io/)
- eSpeak-ng behavior: the existing KokoroG2P `EspeakBackend`

These links are behavioral and API references only. The reference implementation
and its output corpus are not package inputs.

## Data and licensing

KokoroG2P source is Apache-2.0. CAMeL Tools is an optional external dependency,
and its MSA morphology/disambiguation data is a separate external distribution
with separate licensing. No CAMeL or CALIMA data, model weights, or external
reference artifacts are bundled here. CAMeL data must be provisioned locally by
the user through CAMeL Tools' documented workflow; KokoroG2P does not download it.

## Tests and benchmark isolation

Unit tests use independently authored MSA examples, synthetic cleanup strings,
and injected fake adapters. The optional differential benchmark accepts an
explicitly supplied oracle environment and never imports or downloads the
reference automatically. Only comparison metrics and categorized observations
may be recorded in the repository.

The current checkout contains no external oracle run. Differential results must
be recorded only after a maintainer performs that isolated run.
