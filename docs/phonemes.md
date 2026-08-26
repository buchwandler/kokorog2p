# Phoneme Inventory

kokorog2p uses the Kokoro TTS phoneme inventory, which is based on IPA (International
Phonetic Alphabet).

## Kokoro Phoneme Set

The Kokoro phoneme set consists of 45 phonemes plus punctuation markers.

### US English Vowels

#### Monophthongs

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - æ
     - TRAP
     - cat
     - kˈæt
   * - ɑ
     - LOT/PALM
     - father
     - fˈɑðɚ
   * - ə
     - schwa
     - about
     - əbˈaʊt
   * - ɚ
     - r-colored schwa
     - butter
     - bˈʌtɚ
   * - ɛ
     - DRESS
     - bed
     - bˈɛd
   * - ɪ
     - KIT
     - bit
     - bˈɪt
   * - i
     - FLEECE
     - beat
     - bˈit
   * - ʊ
     - FOOT
     - book
     - bˈʊk
   * - u
     - GOOSE
     - boot
     - bˈut
   * - ʌ
     - STRUT
     - cut
     - kˈʌt
   * - ɔ
     - THOUGHT
     - caught
     - kˈɔt
```

#### Diphthongs

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - aɪ
     - PRICE
     - buy
     - bˈaɪ
   * - aʊ
     - MOUTH
     - cow
     - kˈaʊ
   * - eɪ
     - FACE
     - day
     - dˈeɪ
   * - oʊ
     - GOAT
     - go
     - ɡˈoʊ
   * - ɔɪ
     - CHOICE
     - boy
     - bˈɔɪ
```

#### Special Vowels

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - Symbol
     - Name
     - Example Word
     - Phonemes
   * - O
     - GOAT (Kokoro)
     - go
     - ɡˈO
```

Note: `O` is a Kokoro-specific simplification of the GOAT vowel, used instead of `oʊ` in
some contexts.

### Consonants

#### Stops

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - p
     - voiceless bilabial
     - pat
     - pˈæt
   * - b
     - voiced bilabial
     - bat
     - bˈæt
   * - t
     - voiceless alveolar
     - tap
     - tˈæp
   * - d
     - voiced alveolar
     - dad
     - dˈæd
   * - k
     - voiceless velar
     - cat
     - kˈæt
   * - ɡ
     - voiced velar
     - gap
     - ɡˈæp
```

#### Fricatives

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - f
     - voiceless labiodental
     - fat
     - fˈæt
   * - v
     - voiced labiodental
     - vat
     - vˈæt
   * - θ
     - voiceless dental
     - thin
     - θˈɪn
   * - ð
     - voiced dental
     - this
     - ðˈɪs
   * - s
     - voiceless alveolar
     - sip
     - sˈɪp
   * - z
     - voiced alveolar
     - zip
     - zˈɪp
   * - ʃ
     - voiceless postalveolar
     - ship
     - ʃˈɪp
   * - ʒ
     - voiced postalveolar
     - measure
     - mˈɛʒɚ
   * - h
     - glottal
     - hat
     - hˈæt
```

#### Affricates

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - tʃ
     - voiceless postalveolar
     - church
     - tʃˈɚtʃ
   * - dʒ
     - voiced postalveolar
     - judge
     - dʒˈʌdʒ
```

#### Nasals

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - m
     - bilabial
     - map
     - mˈæp
   * - n
     - alveolar
     - nap
     - nˈæp
   * - ŋ
     - velar
     - sing
     - sˈɪŋ
```

#### Liquids

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - l
     - lateral
     - lap
     - lˈæp
   * - ɹ
     - approximant
     - rap
     - ɹˈæp
```

#### Glides

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Phonemes
   * - w
     - labial-velar
     - wap
     - wˈæp
   * - j
     - palatal
     - yap
     - jˈæp
```

### Suprasegmentals

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 30 60

   * - Symbol
     - Name
     - Usage
   * - ˈ
     - Primary stress
     - Placed before the stressed syllable: **ˈ**bæt
   * - ˌ
     - Secondary stress
     - Placed before secondarily stressed syllable: ˌɹɛkəɡnˈɪʃən
```

### Punctuation

Kokoro supports the following punctuation marks:

```text
;  :  ,  .  !  ?  -
```

Other punctuation is typically normalized or removed.

## British English Differences

British English uses most of the same phonemes, with some key differences:

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 20 20 30 30

   * - Phoneme
     - US Example
     - GB Example
     - Difference
   * - ɑ → ɒ
     - lˈɑt (lot)
     - lˈɒt (lot)
     - LOT vowel
   * - ɔ → ɒ
     - kˈɔt (caught)
     - kˈɒt (caught)
     - THOUGHT vowel
   * - ɚ → ə
     - bˈʌtɚ (butter)
     - bˈʌtə (butter)
     - Non-rhotic
   * - oʊ → əʊ
     - ɡˈoʊ (go)
     - ɡˈəʊ (go)
     - GOAT vowel
```

## German Phonemes

German adds several phonemes not found in English:

### Vowels

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Notes
   * - y
     - close front rounded
     - Tür
     - German ü (long)
   * - ʏ
     - near-close front rounded
     - Hütte
     - German ü (short)
   * - ø
     - close-mid front rounded
     - schön
     - German ö (long)
   * - œ
     - open-mid front rounded
     - Köln
     - German ö (short)
   * - aː
     - long a
     - Vater
     - Length distinction
   * - eː
     - long e
     - gehen
     - Length distinction
```

### Consonants

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Notes
   * - ç
     - voiceless palatal fricative
     - ich
     - ich-Laut
   * - x
     - voiceless velar fricative
     - ach
     - ach-Laut
   * - ʁ
     - uvular fricative
     - rot
     - German r
   * - p͡f
     - voiceless labiodental affricate
     - Pferd
     - pf sound
   * - t͡s
     - voiceless alveolar affricate
     - Zeit
     - z sound
```

## French Phonemes

French includes:

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Notes
   * - ɛ̃
     - nasalized open-mid front
     - vin
     - Nasal vowel
   * - ɑ̃
     - nasalized open back
     - sans
     - Nasal vowel
   * - ɔ̃
     - nasalized open-mid back
     - bon
     - Nasal vowel
   * - œ̃
     - nasalized open-mid front rounded
     - un
     - Nasal vowel
   * - ʁ
     - uvular fricative
     - rue
     - French r
```

## Czech Phonemes

Czech includes:

```{eval-rst}
.. list-table::
   :header-rows: 1
   :widths: 10 20 30 40

   * - IPA
     - Name
     - Example Word
     - Notes
   * - r̝
     - raised alveolar trill
     - řeka
     - ř sound
   * - ɟ
     - voiced palatal stop
     - ďábel
     - Palatalized d
   * - c
     - voiceless palatal stop
     - ťava
     - Palatalized t
   * - ɲ
     - palatal nasal
     - nic
     - Palatalized n
   * - ɦ
     - voiced glottal fricative
     - hrad
     - Voiced h
```

## Working with Phonemes

### Validation

```python
from kokorog2p import validate_phonemes

# Valid Kokoro phonemes
assert validate_phonemes("hˈɛlO wˈɜɹld")

# Invalid phonemes
assert not validate_phonemes("xyz123")
```

### Getting Vocabulary

```python
from kokorog2p import get_vocab

# Get US English vocabulary
us_vocab = get_vocab("us")
print(f"US vocabulary: {len(us_vocab)} phonemes")

# Get GB English vocabulary
gb_vocab = get_vocab("gb")
print(f"GB vocabulary: {len(gb_vocab)} phonemes")

# Print all phonemes
for phoneme in us_vocab:
    print(phoneme)
```

## Conversion Between Formats

### espeak to Kokoro

```python
from kokorog2p import from_espeak

# Convert espeak IPA to Kokoro format
espeak_ipa = "həlˈəʊ"
kokoro = from_espeak(espeak_ipa, variant="gb")
print(kokoro)  # hˈɛlO or similar
```

### Kokoro to espeak

```python
from kokorog2p import to_espeak

# Convert Kokoro to espeak IPA
kokoro = "hˈɛlO"
espeak = to_espeak(kokoro, variant="us")
print(espeak)
```

## Nabra Arabic profile

Arabic MSA uses the explicit `nabra-82m-v0.1` vocabulary profile. It is derived from
stock Kokoro 1.0 without mutating that mapping. The profile preserves the dedicated
symbols `ʕ` and `ħ` at IDs 7 and 8 respectively. These IDs are only meaningful when
passed to the compatible Nabra model; they are not a stock Kokoro 1.0 Arabic contract.

## References

- [IPA Chart](https://www.internationalphoneticassociation.org/content/ipa-chart) -
  Official IPA reference
- [Kokoro TTS](https://github.com/hexgrad/Kokoro-82M) - Kokoro TTS model
- [English Phonology](https://en.wikipedia.org/wiki/English_phonology) - Wikipedia
  reference
- [German Phonology](https://en.wikipedia.org/wiki/Standard_German_phonology) -
  Wikipedia reference
