# Swedish provenance

## Runtime implementation

The Swedish frontend is a new clean-room Python rule implementation in `kokorog2p`. No
source code is copied from the upstream neural G2P. The clean-room rule implementation
remains independent from upstream source code.

## Benchmark and data ownership

Development benchmarking may use the external NST-derived pronunciation reference:

- `Joakim/kokoro-sv-g2p/g2p/lexicon.tsv`
- <https://huggingface.co/Joakim/kokoro-sv-g2p/blob/main/g2p/lexicon.tsv>
- Reviewed SHA-256: `65eb3aae9c737f6d04c22a44b2ab836d1ec01f682b1cdee07bb2209852355296`

The source remains a valid external benchmark oracle and is not an infallible claim that
every row is correct. Canonical redistribution and deterministic G2Lex build ownership
is now `g2lex-data`, under the immutable `d19dd10` source pin. KokoroG2P does not bundle
or redistribute the source TSV or generated asset. The source must be provided
explicitly to benchmarks or installed through Lexphon for opt-in runtime lookup.

The existing Apache-2.0 provider, revision, URL, and attribution metadata are preserved.
Underlying Språkbanken/NST provenance should be confirmed separately before adding more
specific attribution or licensing claims.
