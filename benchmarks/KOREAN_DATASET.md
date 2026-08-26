# Korean benchmark dataset

`benchmarks/data/ko_synthetic.json` is a checked-in 100-sentence Korean fixture
containing hand-crafted and CHILDES-derived examples. The benchmark compares
meaningful Korean configurations of the vendored g2pkc-compatible frontend.

## Run

```bash
python benchmarks/benchmark_ko_comparison.py
python benchmarks/benchmark_ko_comparison.py --config "Korean G2P"
python benchmarks/benchmark_ko_comparison.py --config "Korean G2P (morphology auto)"
python benchmarks/benchmark_ko_comparison.py --output results.json
```

The `Korean G2P` configuration runs with morphology off. The auto configuration
uses a supported Korean morphology backend when installed and otherwise falls
back with an actionable warning. Espeak is not a Korean comparison backend.

## Metrics

The script reports exact fixture agreement, sentences per second, total timing,
and unique output characters. The fixture is a regression and performance
reference, not a native-speaker-reviewed pronunciation gold corpus. Results are
environment-dependent and must not be presented as universal accuracy claims.

The default output uses the Kokoro 82M v1.0 model alphabet and the `jf_alpha`
Japanese voice metadata. Use `output="ipa"` or `output="jamo"` in direct API
calls when inspecting linguistic or intermediate representations.

## Alternative backends

Optional differential comparisons belong in a separately provisioned benchmark
environment. Candidates include the exact g2pkc snapshot, upstream g2pK, KSS
with MeCab or Pecab, ko-speech-tools, and mecab-ko. They must report exact
agreement by category and intentional divergences from the local compatibility
baseline rather than selecting a backend by aggregate string agreement alone.
