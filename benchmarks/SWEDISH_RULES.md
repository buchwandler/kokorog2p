# Swedish rule history

The benchmark corpus is external development data. No measured result is claimed until a
local corpus run records the source hash and split.

| rules           | source SHA256 |   split | exact | stressless | PER |
| --------------- | ------------- | ------: | ----: | ---------: | --: |
| v0.1 seed rules | not run       | not run |   n/a |        n/a | n/a |

## v0.1

Rules added: normalization, longest-match SJ and TJ classes, hard and soft G/K/SK, seed
vowel quantity and quality, first-syllable stress, and standard retroflexion. The
benchmark harness is ready for an explicit local `lexicon.tsv`, but the corpus is not
part of this repository.

Known unsolved classes include lexical vowel quality, loanword spelling, compound
stress, alternate pronunciations, and reference rows that may be erroneous. Future
changes must report train, development, and regression results and must state a general
linguistic rationale.
