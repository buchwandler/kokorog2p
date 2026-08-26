# Vietnamese frontend provenance

The Vietnamese frontend is a native clean-room implementation for the `vi-vn`
Northern/Hanoi-oriented broad phonemic profile. The implementation did not inspect,
copy, translate, or depend on `hoang1007/vig2p`. The gold cases are independently
constructed from ordinary Vietnamese vocabulary and the sources below.

## Unicode and tone extraction

Sources:

- Unicode Standard, Chapter 7:
  <https://unicode.org/versions/Unicode16.0.0/core-spec/chapter-7/>
- Vietnamese orthography uses U+0300 grave, U+0309 hook above, U+0303 tilde, U+0301
  acute, and U+0323 dot below for the five marked tones.

Reason: canonical NFC/NFD normalization and combining-mark classification.

## Syllable structure

Sources:

- Vietnamese syllable structure summary:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC9131412/>
- Luong, Vietnamese Speech Synthesis:
  <https://www.isca-archive.org/iscslp_2006/luong06_iscslp.pdf>

Reason: optional onset, medial glide, obligatory nucleus, optional coda, and lexical
tone represented as separate structural fields.

## Inventory and tones

Source:

- ASHA Vietnamese phonology overview:
  <https://pubs.asha.org/doi/10.1044/2023_JSLHR-21-00669>
- Northern Vietnamese tone description:
  <https://www.frontiersin.org/journals/education/articles/10.3389/feduc.2024.1411660/full>

Reason: broad Northern onset, vowel, coda, glide, and six-tone categories. The output
deliberately remains broad rather than claiming narrow allophonic accuracy.

## Model adaptation

Source:

- Kokoro 82M vocabulary is read from this repository's existing
  `kokorog2p/data/kokoro_config.json`.

Reason: Vietnamese rendering is checked against the selected Kokoro model vocabulary.
Unsupported characters are reported instead of silently removed.

## Gold data

`tests/data/vi_gold.json` contains independently selected, human-reviewable examples.
Expected output is structural broad phonology rendered with the named tone markers.
External G2P implementations are not used to generate the curated expected values.
