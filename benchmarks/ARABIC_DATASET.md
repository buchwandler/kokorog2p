# Arabic differential dataset

This is an independently curated smoke dataset for the native Arabic MSA
frontend. It is not copied from an external implementation or output corpus.
The benchmark reads one input per line when given a separate text file.

## Categories

- Vocalized words: `مَرْحَبًا بِكَ`
- Unvocalized words: `اللغة العربية`
- Hamza and long vowels: `هَذَا سُؤَالٌ`
- Shadda and tanwin: `إِنَّ عِلْمًا نَافِعٌ`
- Punctuation: `كَيْفَ حَالُكَ؟`
- Source syntax: `قال [12] مَرْحَبًا (بِكَ)`
- Mixed ASCII Latin: `مَرْحَبًا Hello`

## Differential results

No external oracle run is recorded in this checkout. When a maintainer performs
an isolated comparison, record exact match rate, normalized edit distance,
unsupported-symbol rate, punctuation mismatch rate, `ʕ`/`ħ` preservation, and
suppressed citation/Latin span counts. Categorize remaining differences as
backend, diacritizer, cleanup, or source-normalization differences.

The benchmark script accepts precomputed oracle results with
`--oracle-results`; it never obtains oracle code or data automatically.
