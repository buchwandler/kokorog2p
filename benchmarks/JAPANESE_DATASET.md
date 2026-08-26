# Japanese G2P Benchmark Dataset

## Scope

The checked-in dataset is `benchmarks/data/ja_synthetic.json`. It is a reproducible
coverage and regression corpus, not an independently reviewed pronunciation gold set.
The benchmark harnesses are:

- `benchmarks/benchmark_ja_comparison.py` for backend comparison
- `benchmarks/benchmark_ja_g2p.py` for primary-backend throughput and vocabulary checks

## Running the checks

```bash
python benchmarks/validate_synthetic_data.py benchmarks/data/ja_synthetic.json
python benchmarks/benchmark_ja_comparison.py
python benchmarks/benchmark_ja_comparison.py --config pyopenjtalk
python benchmarks/benchmark_ja_comparison.py --config cutlet
python benchmarks/benchmark_ja_g2p.py --sample-size 5000
```

The comparison benchmark uses `backend="pyopenjtalk"` and `backend="cutlet"`. It does
not expose `+ espeak` variants because Japanese G2P does not implement an espeak
fallback. Unavailable optional backends are reported as unavailable rather than
presented as a zero-quality result.

## Metrics and provenance

The benchmark reports:

- `coverage_rate`: inputs that produced the expected fixture output or a valid result
- `sentences_per_second` or `words_per_second`: warm steady-state throughput
- `encoding_validity_rate` through the vocabulary validation benchmark
- unique output symbols and bounded mismatch samples

Coverage and successful conversion are not pronunciation accuracy. Accuracy requires an
independently reviewed expected output. Each JSON result records the Kokoro package,
Python/platform identity, backend, frontend distribution versions, and Cutlet dictionary
package versions when applicable.

Japanese output is dictionary-sensitive. Compare results only when the frontend and
OpenJTalk dictionary identity are known. Do not compare upstream `pyopenjtalk` and
`pyopenjtalk-plus` in the same environment. They provide the same `pyopenjtalk` import
namespace and must be evaluated in separate clean environments.

## Dataset composition

The dataset contains 371 Japanese sentences covering greetings, common words,
conversation, verbs, adjectives, questions, numbers, punctuation, and natural speech
samples. The current fixture metadata records its exact sentence and phoneme coverage.
Validate the JSON before using it in a benchmark.

## Model-input contract

Japanese token phonemes contain the base Kokoro symbols. `JapaneseG2P.phonemize()`
returns the concatenated model representation: the base phoneme channel followed by an
equally long pitch/control channel. The channels are aligned character by character.
Punctuation, whitespace, long vowels, moraic N, and sokuon are part of the tested
contract.

## Reference and gold data

A generated backend snapshot is useful for parity testing but is not independent gold
data. Future quality work should keep two layers:

- an upstream reference snapshot for deterministic frontend parity
- a smaller hand-reviewed Japanese gold set for pronunciation and model-input review

The current synthetic fixture is not a substitute for that hand-reviewed set.

## Resource and installation contract

`kokorog2p/ja/data/ja_words.txt` is a runtime resource for the retained legacy Cutlet
implementation and is included in built artifacts. The primary installation is:

```bash
pip install "kokorog2p[ja]"
```

Cutlet with the pip-only dictionary is:

```bash
pip install "kokorog2p[ja-cutlet]"
```

Full UniDic is optional and requires an explicit download:

```bash
pip install "kokorog2p[ja-cutlet-full]"
python -m unidic download
```

## Limitations

- The fixture does not establish native-speaker pronunciation accuracy.
- Backend output depends on dictionary and distribution versions.
- Platform installation results come from the CI matrix, not from this document alone.
- Japanese semantic written-to-spoken normalization is not provided by Spokenform.
