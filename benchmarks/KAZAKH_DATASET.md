# Kazakh benchmark dataset

`benchmark_kk_espeak.py` uses a compact diagnostic corpus covering:

- Kazakh-specific letters in upper and lower case, including multiple word positions.
- Common words and short sentences.
- Numbers, decimal input, punctuation, and mixed Latin/Cyrillic text.
- The eSpeak-NG voice identifier `kk`.

The benchmark records raw eSpeak IPA, normalized Kokoro labels, invalid vocabulary symbols,
model validity, and transform-rule hit counts. It is diagnostic rather than a quality gold
standard because upstream eSpeak-NG currently marks the Kazakh voice as `testing`.

Run it with:

```bash
python benchmarks/benchmark_kk_espeak.py
python benchmarks/benchmark_kk_espeak.py --json out/kk_espeak.json
python benchmarks/benchmark_kk_espeak.py --show-failures
python benchmarks/benchmark_kk_espeak.py --strict
```

Optional Epitran output is available only as a differential diagnostic and never makes a
mismatch a test failure:

```bash
python benchmarks/benchmark_kk_espeak.py --epitran
```
