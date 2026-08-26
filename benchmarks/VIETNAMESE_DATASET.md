# Vietnamese benchmark dataset

The benchmark uses the independently authored cases in `tests/data/vi_gold.json`. The
target is broad Northern/Hanoi Vietnamese (`vi-vn-north`). The cases cover named tones,
onset families, principal nuclei, medial and off-glides, nasal and stop codas, NFC/NFD
input, punctuation, and ASCII-only syllables.

The expected values are human-reviewable structural outputs and are not copied from a
legacy engine. External engines, when installed, are diagnostic comparisons only.
Disagreements are classified as orthography, dialect, tone, vowel, coda, routing,
normalization, punctuation, or model-rendering issues. The current fixture is a seed
corpus for the first implementation; expanding it toward the 200-500-case release
recommendation requires additional native speaker review.
