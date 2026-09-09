# French Synthetic Benchmark Dataset

## Overview

French dictionary benchmarks use the externally provisioned Lexphon asset `fr-fr:gold`.
KokoroG2P no longer ships a French dictionary or a tiered comparison script.

## Quick Start

```bash
lexphon data install fr-fr:gold
lexphon data verify fr-fr:gold
```

Use `FrenchG2P(lexicons="gold")` for dictionary-backed measurements and
`FrenchG2P(lexicons=())` for fallback-only measurements.

## Benchmark Results (154 sentences, 650 words)

| Configuration | Accuracy | Speed        | Recommendation   |
| ------------- | -------- | ------------ | ---------------- |
| Gold only     | 100.0%   | 9,399 sent/s | ✅ **Best**      |
| Gold + Goruut | 100.0%   | 7,783 sent/s | Good alternative |
| Gold + Espeak | 100.0%   | 7,669 sent/s | Good alternative |
| Espeak only   | 44.2%    | 1,059 sent/s | Not recommended  |
| Goruut only   | 20.8%    | 54 sent/s    | Not recommended  |

**Recommendation**: Use **Gold only** configuration for French. The gold lexicon (15,011
entries) provides excellent coverage of common French vocabulary with perfect accuracy
and best speed.

## Dataset Composition

The dataset consists of:

- **35 hand-crafted sentences** covering:
  - Greetings (Bonjour, Comment allez-vous?, etc.)
  - Common words and phrases
  - Conversational French
  - Numbers and counting
  - Phoneme coverage testing
- **119 natural speech samples** from CHILDES fr-FR corpus (adult speech only)

**Total**: 154 sentences with 650 words

## Phoneme Coverage

The dataset achieves **100% coverage** of all 35 French phoneme characters:

```
' , - a b d e f i j k l m n o p s t u v w y z ø œ ɑ ɔ ə ɛ ɡ ɥ ʁ ʃ ʒ ̃
```

### French Nasal Vowels

French uses combining diacritics for nasal vowels. The tilde (̃, U+0303) combines with
the vowel:

- **ɑ̃** - nasal A (dans, enfant, temps)
- **ɛ̃** - nasal E (vin, pain, bien)
- **œ̃** - nasal EU (un, parfum)
- **ɔ̃** - nasal O (bon, monde, nom)

**Note**: Each nasal vowel counts as 2 characters (base + combining tilde) but
represents 1 phoneme.

### French Oral Vowels

- **a** - open front (chat, la)
- **ɑ** - open back (pâte, bas)
- **e** - close front (été, les)
- **ɛ** - open-mid front (père, mais)
- **ə** - schwa (le, de, je)
- **i** - close front (si, vie)
- **o** - close-mid back (beau, tôt)
- **ɔ** - open-mid back (porte, mort)
- **ø** - close-mid front rounded (peu, deux)
- **œ** - open-mid front rounded (peur, sœur)
- **u** - close back rounded (tout, vous)
- **y** - close front rounded (tu, vu)

### French Consonants

**Special French sounds:**

- **ʁ** - uvular fricative (French R: rouge, Paris)
- **ʃ** - voiceless postalveolar fricative (ch: chat, chaud)
- **ʒ** - voiced postalveolar fricative (j: je, rouge)
- **ɥ** - labial-palatal approximant (ui: huit, nuit)
- **ɲ** - palatal nasal (gn: agneau, montagne) - Note: Not in current vocab set

**Standard consonants:**

- **b d f ɡ k l m n p s t v w z** - similar to English
- **j** - palatal approximant (y: yeux, payer)

### Punctuation and Stress

- **'** - apostrophe (l'ami, c'est)
- **,** - comma (pause marker)
- **-** - hyphen (compound words)

**Note**: French does not use lexical stress like English. Stress typically falls on the
final syllable of phrases.

## Category Breakdown

| Category         | Sentences | Description                              |
| ---------------- | --------- | ---------------------------------------- |
| childes_natural  | 119       | Natural adult speech from CHILDES corpus |
| common_words     | 8         | Frequently used vocabulary               |
| greetings        | 4         | Common French greetings                  |
| conversation     | 5         | Conversational phrases                   |
| phoneme_coverage | 6         | Sentences ensuring all phonemes present  |
| numbers          | 3         | Number pronunciation                     |

## G2P Backend Information

### Gold Lexicon (Recommended)

The French gold lexicon contains **15,011 entries** covering:

- Most common French words
- Frequent verb forms
- Common expressions
- Numbers and basic vocabulary

**Performance**: 100% accuracy on benchmark, 9,399 sent/s

### Espeak-ng Fallback

espeak-ng provides phoneme predictions for OOV words:

- Handles rare/technical vocabulary
- Rule-based pronunciation
- Lower accuracy than lexicon (44.2% standalone)
- Adds ~18% overhead when combined with gold

### Goruut Fallback

Goruut provides alternative phoneme predictions:

- Uses neural G2P approach
- Better for uncommon words than espeak
- Much slower (54 sent/s standalone)
- Adds ~17% overhead when combined with gold

## CHILDES Corpus Source

The natural speech examples were extracted from:

- **Corpus**: CHILDES IPA corpus
- **Language**: fr-FR (French)
- **Source size**: 187.8 MB (~649K sentences)
- **Selection criteria**:
  - Adult speech only (not child babbling)
  - 3-10 tokens per sentence
  - Valid French characters
  - No OOV phonemes (no "?" markers)
  - Deduplicated against hand-crafted sentences

**Extraction rate**: ~0.04% (119 sentences from ~300K candidates)

- High filtering rate due to strict phoneme quality criteria
- Many sentences rejected due to unknown phonemes in CHILDES
- Focus on grammatical, complete adult utterances

### CHILDES Extraction Challenges

French CHILDES data presented unique challenges:

1. **High OOV rate**: ~63% of extracted sentences contained unknown phonemes (marked
   with "?")
2. **Filtering strategy**: Extracted in batches, regenerated phonemes with FrenchG2P,
   removed invalid sentences
3. **Lower yield**: Compared to German (189 sentences) or Japanese (371 sentences),
   French had lower retention
4. **Quality over quantity**: Prioritized phoneme accuracy over dataset size

## Usage Examples

### Basic Benchmarking

```python
from kokorog2p.fr import FrenchG2P

# Create G2P with recommended configuration (gold only)
g2p = FrenchG2P()

# Phonemize French text
tokens = g2p("Bonjour tout le monde")
for token in tokens:
    print(f"{token.text} → {token.phonemes}")
# Output:
# Bonjour → bɔ̃ʒuʁ
# tout → tu
# le → lə
# monde → mɔ̃d
```

### Testing Different Configurations

```python
from kokorog2p.fr import FrenchG2P

# Gold lexicon only (recommended)
g2p_gold = FrenchG2P()

# Gold + espeak fallback (better OOV coverage)
g2p_espeak = FrenchG2P(use_espeak_fallback=True)

# Gold + goruut fallback (alternative OOV handling)
g2p_goruut = FrenchG2P(use_goruut_fallback=True)

# Test with OOV word
text = "antibiotique"  # may not be in lexicon
print("Gold only:", [t.phonemes for t in g2p_gold(text)])
print("Gold + Espeak:", [t.phonemes for t in g2p_espeak(text)])
```

### Running measurements

Provision `fr-fr:gold` as shown above, then run the focused French regression tests or
your local benchmark harness with `lexicons="gold"` and `lexicons=()` modes.

## Validation Results

Run the validator to check dataset integrity:

```bash
python benchmarks/validate_synthetic_data.py benchmarks/data/fr_synthetic.json
```

**Results**:

- ✅ All 154 sentences validated
- ✅ 100% phoneme coverage (35/35 unique characters)
- ✅ No invalid phonemes
- ✅ All required fields present

## Known Limitations

1. **Smaller dataset**: 154 sentences is smaller than German (189) or Japanese (371) due
   to CHILDES filtering challenges
2. **External provisioning**: The `fr-fr:gold` asset is released and installed through Lexphon
3. **Liaison not represented**: French liaison (linking) is not explicitly marked in
   phonemes
4. **Elision handling**: Contractions like "l'ami" are treated as separate tokens
5. **Regional variation**: Dataset represents standard Parisian French pronunciation
6. **No ɲ phoneme**: The gn sound (ɲ) is not in the current Kokoro French phoneme set

## French Phonological Features

### Nasal Vowels

French is famous for nasal vowels, which don't exist in English:

- **ɑ̃** in "dans" (in), "enfant" (child)
- **ɛ̃** in "vin" (wine), "pain" (bread)
- **œ̃** in "un" (one), rarely used in modern French
- **ɔ̃** in "bon" (good), "monde" (world)

### Uvular R

The French R (ʁ) is a uvular fricative, pronounced at the back of the throat:

- "rouge" → ʁuʒ
- "Paris" → paʁi

### Front Rounded Vowels

French has rounded front vowels not found in English:

- **ø** in "peu" (few) - like German ö
- **œ** in "peur" (fear) - like German ö but more open
- **y** in "tu" (you) - like German ü

### No Lexical Stress

Unlike English or German, French has no lexical stress on individual words. Stress falls
on the final syllable of phrases.

## Future Improvements

Potential areas for enhancement:

- [ ] Add broader vocabulary to the upstream `fr-fr:gold` release
- [ ] Include more technical/scientific vocabulary
- [ ] Add regional pronunciation variants (Belgian, Swiss, Quebec)
- [ ] Test liaison handling explicitly
- [ ] Add more numbers and dates
- [ ] Include compound tenses and verb forms

## References

- CHILDES IPA Corpus: https://github.com/ErikMorton/ipa-childes
- French IPA: https://en.wikipedia.org/wiki/Help:IPA/French
- Kokoro TTS French: https://github.com/hexgrad/kokoro-onnx
- espeak-ng French: https://github.com/espeak-ng/espeak-ng

## Contributing

To improve the French dataset:

1. Add more diverse sentence patterns (questions, commands, etc.)
2. Test with specialized vocabulary (medical, legal, technical)
3. Validate pronunciation with native French speakers
4. Report any phoneme mismatches or errors
5. Add examples of liaison and elision

## License

The French synthetic dataset is released under the same license as kokorog2p.
