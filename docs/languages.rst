Language Support
================

kokorog2p supports multiple languages with varying levels of functionality.

.. list-table:: Language Support Overview
   :header-rows: 1
   :widths: 15 15 20 20 30

   * - Language
     - Code
     - Dictionary
     - Fallback
     - Special Features
   * - English (US)
     - en-us
     - 100k+ entries
     - espeak-ng
     - POS tagging, stress, numbers
   * - English (GB)
     - en-gb
     - 100k+ entries
     - espeak-ng
     - POS tagging, stress, numbers
   * - German
     - de
     - 738k+ entries
     - espeak-ng
     - Phonological rules, numbers
   * - French
     - fr
     - Gold dictionary
     - espeak-ng
     - Numbers, liaison rules
   * - Spanish
     - es
     - Rule-based
     - espeak-ng/goruut
     - Phonological rules, numbers
   * - Italian
     - it
     - Rule-based
     - espeak-ng/goruut
     - Phonological rules, gemination
   * - Portuguese
     - pt
     - Rule-based
     - —
     - Phonological rules, nasalization
   * - Czech
     - cs
     - Rule-based
     - espeak-ng/goruut
     - Phonological rules
   * - Chinese
     - zh
     - —
     - pypinyin
     - Tone sandhi, pinyin
   * - Japanese
     - ja
     - —
     - pyopenjtalk
     - Mora-based, pitch accent
   * - Korean
     - ko
     - —
     - MeCab
     - Phonological rules, liaison
   * - Hebrew
     - he
     - —
     - phonikud
     - Nikud handling, stress
   * - Mixed
     - multilingual
     - Auto-detect
     - lingua-py
     - 17+ languages, word-level detection

English (en-us, en-gb)
----------------------

English G2P uses a two-tier dictionary system with spaCy for POS tagging.

Features
~~~~~~~~

* **Gold dictionary**: 50k+ high-confidence entries
* **Silver dictionary**: Additional 50k+ entries
* **POS-aware pronunciation**: Different pronunciations based on part of speech
* **Stress assignment**: Primary and secondary stress markers
* **Number handling**: Cardinals, ordinals, currency
* **Contraction support**: Proper handling of "can't", "won't", etc.

Usage
~~~~~

.. code-block:: python

   from kokorog2p.en import EnglishG2P

   # US English
   g2p_us = EnglishG2P(
       language="en-us",
       use_espeak_fallback=True,
       use_spacy=True
   )

   # British English
   g2p_gb = EnglishG2P(
       language="en-gb",
       use_espeak_fallback=True,
       use_spacy=True
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   # Context-dependent pronunciation
   print(phonemize("I read a book.", language="en-us"))
   # → ˈaɪ ɹˈɛd ə bˈʊk.

   print(phonemize("I will read tomorrow.", language="en-us"))
   # → ˈaɪ wɪl ɹˈid təmˈɑɹO.

   # Numbers and currency
   print(phonemize("I paid $1,234.56 for it.", language="en-us"))
   # → aɪ pˈeɪd wʌn θˈaʊzənd tˈu hˈʌndɹəd...

German (de)
-----------

German G2P uses a large dictionary (738k+ entries from Olaph) with rule-based fallback.

Features
~~~~~~~~

* **Large dictionary**: 738k+ entries with stress markers
* **Phonological rules**:

  - Final obstruent devoicing (Auslautverhärtung)
  - ich-Laut [ç] vs ach-Laut [x] alternation
  - Word-initial sp/st → [ʃp]/[ʃt]
  - Vowel length rules
  - Schwa in unstressed syllables

* **Number handling**: Cardinals, ordinals, years, currency
* **Regional variants**: de-de, de-at, de-ch

Usage
~~~~~

.. code-block:: python

   from kokorog2p.de import GermanG2P

   g2p = GermanG2P(
       language="de-de",
       use_espeak_fallback=True,
       strip_stress=True
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   # Basic phonemization
   print(str(phonemize("Guten Tag", language="de")))
   # → ɡuːtn̩ taːk

   # Phonological rules
   print(str(phonemize("ich", language="de")))      # → ɪç (ich-Laut)
   print(str(phonemize("ach", language="de")))      # → ax (ach-Laut)
   print(str(phonemize("Tag", language="de")))      # → taːk (final devoicing)

   # Numbers
   print(str(phonemize("Ich habe 42 Euro.", language="de")))
   # → ɪç haːbə t͡svaɪ̯ʊntfɪɐ̯t͡sɪç ɔɪ̯ʁo.

French (fr)
-----------

French G2P uses a gold dictionary with espeak-ng fallback.

Features
~~~~~~~~

* **Gold dictionary**: High-quality French pronunciations
* **Number handling**: Cardinals, ordinals, currency
* **espeak-ng fallback**: For out-of-vocabulary words

Usage
~~~~~

.. code-block:: python

   from kokorog2p.fr import FrenchG2P

   g2p = FrenchG2P(
       language="fr-fr",
       use_espeak_fallback=True
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("Bonjour le monde", language="fr"))
   # → bɔ̃ʒuʁ lə mɔ̃d

   print(phonemize("J'ai vingt et un ans.", language="fr"))
   # → ʒɛ vɛ̃t e œ̃ ɑ̃.

Czech (cs)
----------

Czech G2P is entirely rule-based with comprehensive phonological rules.

Features
~~~~~~~~

* **Rule-based phonology**:

  - Palatalization (d+i → ɟ, t+i → c, n+i → ɲ)
  - Long vowels (á → aː, í → iː, etc.)
  - ř phoneme [r̝]
  - ch digraph → [x]
  - Final devoicing
  - Voicing assimilation

* **No dictionary required**: Works with any Czech text

Usage
~~~~~

.. code-block:: python

   from kokorog2p.cs import CzechG2P

   g2p = CzechG2P(language="cs-cz")

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("Dobrý den", language="cs"))
   # → dobriː dɛn

   print(phonemize("Praha", language="cs"))
   # → praɦa

   # Palatalization
   print(phonemize("děti", language="cs"))
   # → ɟɛcɪ

    # ř phoneme
    print(phonemize("řeka", language="cs"))
    # → r̝ɛka

Spanish (es)
------------

Spanish G2P is rule-based with comprehensive phonological rules for both European and Latin American dialects.

Features
~~~~~~~~

* **Rule-based phonology**:

  - 5 pure vowels (a, e, i, o, u)
  - Stress prediction (penultimate for vowel-ending, final for consonant-ending)
  - Palatal sounds: ñ [ɲ], ll [ʎ] or [j]
  - Jota: j/g+e/i [x]
  - Theta: z/c+e/i [θ] (European) or [s] (Latin American)
  - Tap vs trill: r [ɾ] vs rr [r]

* **Dialect support**: es (European), la (Latin American)
* **Number handling**: Cardinals, ordinals, currency

Usage
~~~~~

.. code-block:: python

   from kokorog2p.es import SpanishG2P

   g2p = SpanishG2P(
       language="es",
       dialect="es"  # or "la" for Latin American
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("Hola mundo", language="es"))
   # → ola mundo

   # Phonological features
   print(phonemize("año", language="es"))      # → aɲo
   print(phonemize("calle", language="es"))    # → kaʎe or kaje
   print(phonemize("perro", language="es"))    # → pero (trilled r)

Italian (it)
------------

Italian G2P uses rule-based phonology with predictable stress and gemination handling.

Features
~~~~~~~~

* **Rule-based phonology**:

  - 5 pure vowels (a, e, i, o, u) - no reduction
  - Predictable stress (usually penultimate)
  - Gemination (double consonants) preservation
  - Palatals: gn [ɲ], gli [ʎ]
  - Affricates: z [ʦ/ʣ], c/ci [ʧ], g/gi [ʤ]
  - Context-sensitive c/g pronunciation

* **Stress marking**: Automatic stress detection from accents
* **Number handling**: Cardinals, ordinals

Usage
~~~~~

.. code-block:: python

   from kokorog2p.it import ItalianG2P

   g2p = ItalianG2P(
       language="it-it",
       mark_stress=True,
       mark_gemination=True
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("Ciao mondo", language="it"))
   # → ʧao mondo

   # Gemination
   print(phonemize("anno", language="it"))     # → anːo
   print(phonemize("fatto", language="it"))    # → fatːo

   # Palatals
   print(phonemize("gnocchi", language="it"))  # → ɲɔkːi
   print(phonemize("figlio", language="it"))   # → fiʎo

Portuguese (pt)
---------------

Portuguese G2P supports Brazilian Portuguese with comprehensive phonological rules.

Features
~~~~~~~~

* **Rule-based phonology**:

  - 7 oral vowels (a, e, ɛ, i, o, ɔ, u)
  - 5 nasal vowels (ã, ẽ, ĩ, õ, ũ)
  - Nasal diphthongs
  - Palatalization: lh [ʎ], nh [ɲ], x/ch [ʃ]
  - Affrication: t+i [ʧ], d+i [ʤ] (Brazilian)
  - Sibilants: s [s/z], x [ʃ], z [z]
  - Liquids: r [ʁ/x/h], rr [ʁ/x], single r [ɾ]

* **Dialect**: Brazilian Portuguese (pt-br)
* **Stress marking**: Automatic stress assignment

Usage
~~~~~

.. code-block:: python

   from kokorog2p.pt import PortugueseG2P

   g2p = PortugueseG2P(
       language="pt-br",
       mark_stress=True,
       affricate_ti_di=True  # Brazilian feature
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("Olá mundo", language="pt"))
   # → ola mundo

   # Nasal vowels
   print(phonemize("mãe", language="pt"))      # → mãj̃
   print(phonemize("pão", language="pt"))      # → pãw̃

   # Affrication (Brazilian)
   print(phonemize("tia", language="pt"))      # → ʧia
   print(phonemize("dia", language="pt"))      # → ʤia

Chinese (zh)
------------

Chinese G2P uses jieba for tokenization and pypinyin for phoneme conversion.

Features
~~~~~~~~

* **Jieba tokenization**: Chinese word segmentation
* **Pypinyin conversion**: Pinyin to IPA
* **Tone sandhi**: Automatic tone changes
* **cn2an**: Number to Chinese conversion
* **Punctuation mapping**: Chinese to Western punctuation

Usage
~~~~~

.. code-block:: python

   from kokorog2p.zh import ChineseG2P

   g2p = ChineseG2P(
       language="zh",
       version="1.1"
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("你好世界", language="zh"))
   # → nǐ hǎo shì jiè (with tone markers)

Japanese (ja)
-------------

Japanese G2P uses pyopenjtalk for text analysis and mora-based phoneme generation.

Features
~~~~~~~~

* **pyopenjtalk**: Full Japanese text analysis
* **Mora-based**: Phonemes aligned with mora structure
* **Pitch accent**: Automatic pitch accent assignment
* **Number handling**: Japanese numerals

Usage
~~~~~

.. code-block:: python

   from kokorog2p.ja import JapaneseG2P

   g2p = JapaneseG2P(
       language="ja",
       version="pyopenjtalk"
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("こんにちは", language="ja"))
   # → koɴɲit͡ɕiha

   print(phonemize("世界", language="ja"))
   # → sekai

Korean (ko)
-----------

Korean G2P uses MeCab-based morphological analysis with comprehensive phonological rules.

Features
~~~~~~~~

* **MeCab integration**: Korean morphological analysis
* **Phonological rules**:

  - Consonant assimilation
  - Palatalization
  - Tensification
  - Aspiration
  - Liaison (연음)
  - Final consonant neutralization

* **Hanja support**: Sino-Korean character handling
* **Number handling**: Korean numerals

Usage
~~~~~

.. code-block:: python

   from kokorog2p.ko import KoreanG2P

   g2p = KoreanG2P(
       language="ko-kr",
       use_mecab=True
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   print(phonemize("안녕하세요", language="ko"))
   # → annjʌŋhasejo

   # Phonological rules
   print(phonemize("학교", language="ko"))     # → hakk͈jo (tensification)
   print(phonemize("받침", language="ko"))     # → patʃʰim (palatalization)

Hebrew (he)
-----------

Hebrew G2P uses phonikud for nikud-based phonemization.

Features
~~~~~~~~

* **phonikud integration**: Hebrew nikud to IPA conversion
* **Nikud handling**: Processes diacritical marks for vowels
* **Stress prediction**: Automatic stress assignment
* **Modern Hebrew**: Optimized for contemporary pronunciation

Usage
~~~~~

.. code-block:: python

   from kokorog2p.he import HebrewG2P

   g2p = HebrewG2P(
       language="he-il",
       preserve_punctuation=True,
       preserve_stress=True
   )

Examples
~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   # Requires nikud (diacritical marks)
   print(phonemize("שָׁלוֹם", language="he"))
   # → ʃalom

   print(phonemize("עִבְרִית", language="he"))
   # → ivʁit

Mixed-Language Support
----------------------

kokorog2p can automatically detect and handle texts that mix multiple languages, routing each word to the appropriate G2P engine.

Features
~~~~~~~~

* **Automatic detection**: Word-level language detection using lingua-py
* **High accuracy**: >90% accuracy for words with 5+ characters
* **Caching**: Detection results cached for performance
* **Configurable threshold**: Control detection sensitivity
* **Graceful degradation**: Falls back to primary language without lingua-py
* **17+ languages**: Support for major world languages

Supported Languages
~~~~~~~~~~~~~~~~~~~

* English (en-us, en-gb)
* German (de)
* French (fr)
* Spanish (es)
* Italian (it)
* Portuguese (pt)
* Japanese (ja)
* Chinese (zh)
* Korean (ko)
* Hebrew (he)
* Czech (cs)
* Dutch (nl)
* Polish (pl)
* Russian (ru)
* Arabic (ar)
* Hindi (hi)
* Turkish (tr)

Usage
~~~~~

.. code-block:: python

   from kokorog2p import phonemize
   from kokorog2p.multilang import preprocess_multilang

   text = "Das Meeting war great!"
   overrides = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us"],
   )

   result = phonemize(text, lang="de", overrides=overrides, result_type="result")

Examples
~~~~~~~~

**German with English:**

.. code-block:: python

   from kokorog2p import phonemize
   from kokorog2p.multilang import preprocess_multilang

   text = "Ich gehe zum Meeting. Let's discuss the Roadmap!"
   overrides = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us"],
   )
   result = phonemize(text, lang="de", overrides=overrides, result_type="result")
   print(result.phonemes)

**English with German:**

.. code-block:: python

   overrides = preprocess_multilang(
       "Hello, mein Freund! This is wunderbar.",
       default_language="en-us",
       allowed_languages=["en-us", "de"],
   )
   result = phonemize(
       "Hello, mein Freund! This is wunderbar.",
       language="en-us",
       overrides=overrides)
   )
   print(result.phonemes)

**Multiple languages:**

.. code-block:: python

   overrides = preprocess_multilang(
       "Bonjour! The Meeting ist wichtig.",
       default_language="fr",
       allowed_languages=["fr", "en-us", "de"],
   )
   result = phonemize(
       "Bonjour! The Meeting ist wichtig.",
       language="fr",
       overrides=overrides,
   )
   print(result.phonemes)

Configuration
~~~~~~~~~~~~~

**Confidence threshold:**

.. code-block:: python

   from kokorog2p.multilang import preprocess_multilang

   # Conservative (higher confidence required)
   overrides = preprocess_multilang(
       "Das Meeting ist wichtig",
       default_language="de",
       allowed_languages=["de", "en-us"],
       confidence_threshold=0.9,  # Default: 0.7
   )

   # Aggressive (lower confidence required)
   overrides = preprocess_multilang(
       "Das Meeting ist wichtig",
       default_language="de",
       allowed_languages=["de", "en-us"],
       confidence_threshold=0.5,
   )

How It Works
~~~~~~~~~~~~

1. Text is tokenized into words
2. Each word is sent to the language detector
3. Detector returns language + confidence score
4. If confidence ≥ threshold and language is allowed:

   * An ``OverrideSpan`` is created with ``{"lang": "..."}``
   * Short words (<3 chars) keep the default language

Performance
~~~~~~~~~~~

* **Memory**: ~100 MB for lingua models (loaded once)
* **Speed**: ~0.1-0.5 ms per word
* **Accuracy**: >90% for words with 5+ characters

Limitations
~~~~~~~~~~~

* Short words (<3 characters) use the default language only
* Proper nouns may be misdetected
* Requires ``lingua-language-detector`` installation
* Detection quality varies by word distinctiveness

Installation
~~~~~~~~~~~~

.. code-block:: bash

   pip install kokorog2p[mixed]

Language-Specific Number Handling
----------------------------------

English
~~~~~~~

.. code-block:: python

   from kokorog2p.en.numbers import expand_number

   print(expand_number("I have $42.50"))
   # → I have forty-two dollars and fifty cents

German
~~~~~~

.. code-block:: python

   from kokorog2p.de.numbers import expand_number

   print(expand_number("Ich habe 42 Euro."))
   # → Ich habe zweiundvierzig Euro.

French
~~~~~~

.. code-block:: python

   from kokorog2p.fr.numbers import expand_number

   print(expand_number("J'ai 42 euros."))
   # → J'ai quarante-deux euros.

Fallback Languages
------------------

For languages not explicitly supported, kokorog2p falls back to espeak-ng:

.. code-block:: python

   from kokorog2p import get_g2p

   # Spanish (uses espeak-ng)
   g2p_es = get_g2p("es-es")

   # Italian (uses espeak-ng)
   g2p_it = get_g2p("it-it")

   # Portuguese (uses espeak-ng)
   g2p_pt = get_g2p("pt-br")

This provides basic support for 100+ languages via espeak-ng.

Next Steps
----------

* See :doc:`advanced` for advanced usage patterns
* Check language-specific API docs:

  - :doc:`api/english`
  - :doc:`api/german`
  - :doc:`api/french`
  - :doc:`api/czech`
  - :doc:`api/spanish`
  - :doc:`api/italian`
  - :doc:`api/portuguese`
  - :doc:`api/chinese`
  - :doc:`api/japanese`
  - :doc:`api/korean`
  - :doc:`api/hebrew`
  - :doc:`api/mixed`
