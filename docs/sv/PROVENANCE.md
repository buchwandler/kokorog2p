# Swedish provenance

## Runtime implementation

The Swedish frontend is a new clean-room Python rule implementation in `kokorog2p`. No
source code is copied from the upstream neural G2P. No upstream lexicon is bundled with
or loaded by the runtime package.

## Benchmark reference

Development benchmarking may use:

- `Joakim/kokoro-sv-g2p/g2p/lexicon.tsv`
- <https://huggingface.co/Joakim/kokoro-sv-g2p/blob/main/g2p/lexicon.tsv>
- Reviewed SHA256: `65eb3aae9c737f6d04c22a44b2ab836d1ec01f682b1cdee07bb2209852355296`

The TSV is an external NST-derived pronunciation reference. It must be provided
explicitly to the benchmark and is not runtime data. The source is a benchmark oracle,
not an infallible claim that every row is correct. Underlying Språkbanken/NST provenance
should be confirmed separately before adding more specific attribution.
