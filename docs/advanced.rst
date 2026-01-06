Advanced Usage
==============

This guide covers advanced features and usage patterns for kokorog2p.

Custom G2P Configuration
------------------------

Memory-Efficient Loading
~~~~~~~~~~~~~~~~~~~~~~~~

Control dictionary loading to optimize memory and initialization time:

.. code-block:: python

   from kokorog2p import get_g2p

   # Default: Gold + Silver dictionaries (~365k entries, ~57 MB)
   # Provides maximum vocabulary coverage
   g2p = get_g2p("en-us")

   # Memory-optimized: Gold dictionary only (~179k entries, ~35 MB)
   # Saves ~22-31 MB memory and ~400-470 ms initialization time
   g2p_fast = get_g2p("en-us", load_silver=False)

   # Ultra-fast initialization: No dictionaries (~7 MB, espeak fallback only)
   # Saves ~50+ MB memory, fastest initialization
   g2p_minimal = get_g2p("en-us", load_silver=False, load_gold=False)

   # Check dictionary size
   print(f"Gold entries: {len(g2p.lexicon.golds):,}")
   print(f"Silver entries: {len(g2p.lexicon.silvers):,}")

**Dictionary loading configurations:**

* ``load_gold=True, load_silver=True``: Maximum coverage (default, ~365k entries)
* ``load_gold=True, load_silver=False``: Common words only (~179k entries, -22-31 MB)
* ``load_gold=False, load_silver=True``: Extended vocabulary only (unusual, ~187k entries)
* ``load_gold=False, load_silver=False``: Ultra-fast (espeak only, -50+ MB)

**When to disable dictionaries:**

* **Disable silver** (``load_silver=False``):
  * Resource-constrained environments (limited memory)
  * Real-time applications (faster initialization)
  * You only need common vocabulary
  * Production deployments where performance is critical

* **Disable both** (``load_gold=False, load_silver=False``):
  * Ultra-fast initialization is critical
  * You're fine with espeak-only fallback
  * Minimal memory footprint required
  * Testing or prototyping

**Default (both enabled) provides:**

* Maximum vocabulary coverage (~365k total entries)
* Best phoneme quality from curated dictionaries
* Backward compatibility with existing code

Disabling Features
~~~~~~~~~~~~~~~~~~

You can disable specific features for better performance or control:

.. code-block:: python

   from kokorog2p.en import EnglishG2P

   # Disable espeak fallback
   g2p = EnglishG2P(
       language="en-us",
       use_espeak_fallback=False,  # Unknown words will have no phonemes
       use_spacy=True
   )

   # Disable spaCy (faster but no POS tagging)
   g2p = EnglishG2P(
       language="en-us",
       use_espeak_fallback=True,
       use_spacy=False  # Faster tokenization
   )

   # Minimal configuration (fastest)
   g2p = EnglishG2P(
       language="en-us",
       use_espeak_fallback=False,
       use_spacy=False,
       load_silver=False,
       load_gold=False  # No dictionaries, ultra-fast
   )

Stress Control
~~~~~~~~~~~~~~

Control stress marker output:

.. code-block:: python

   from kokorog2p.de import GermanG2P

   # Strip stress markers from output
   g2p = GermanG2P(
       language="de-de",
       strip_stress=True  # Remove ˈ and ˌ markers
   )

Token Inspection
----------------

Tokens contain detailed information:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p("en-us", use_spacy=True)
   tokens = g2p("I can't believe it!")

   for token in tokens:
       # Basic attributes
       print(f"Text: {token.text}")
       print(f"Phonemes: {token.phonemes}")
       print(f"POS tag: {token.tag}")
       print(f"Whitespace: '{token.whitespace}'")

       # Additional metadata
       rating = token.get("rating")  # 5=dictionary, 2=espeak, 0=unknown
       print(f"Rating: {rating}")

       # Check token type
       is_punct = not any(c.isalnum() for c in token.text)
       print(f"Is punctuation: {is_punct}")

Rating System
~~~~~~~~~~~~~

Tokens have a rating indicating the source of phonemes:

* **5**: User-provided (markdown annotations) or gold dictionary (highest quality)
* **4**: Punctuation
* **3**: Silver dictionary or rule-based conversion
* **2**: From espeak-ng fallback
* **1**: From goruut backend
* **0**: Unknown/failed

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p("en-us")
   tokens = g2p("Hello xyznotaword!")

   for token in tokens:
       rating = token.get("rating", 0)
       if rating == 5:
           print(f"{token.text}: High quality (gold dictionary)")
       elif rating == 3:
           print(f"{token.text}: Silver dictionary")
       elif rating == 2:
           print(f"{token.text}: Fallback (espeak)")
       elif rating == 0:
           print(f"{token.text}: Unknown")

Dictionary Lookup
-----------------

Direct dictionary access:

.. code-block:: python

   from kokorog2p.en import EnglishG2P

   # Load with or without silver dataset
   g2p_gold = EnglishG2P(language="en-us", load_silver=False)
   g2p_full = EnglishG2P(language="en-us", load_silver=True)

   # Simple lookup
   phonemes = g2p_gold.lexicon.lookup("hello")
   print(phonemes)  # həlˈO

   # Check if word is in dictionary
   if g2p_gold.lexicon.is_known("hello"):
       print("Word is in gold dictionary")

   # Get dictionary sizes
   print(f"Gold: {len(g2p_gold.lexicon.golds):,} entries")
   print(f"Silver: {len(g2p_full.lexicon.silvers):,} entries")

   # POS-aware lookup
   phonemes_verb = g2p_gold.lexicon.lookup("read", tag="VB")   # ɹˈid (present)
   phonemes_past = g2p_gold.lexicon.lookup("read", tag="VBD")  # ɹˈɛd (past)

German Lexicon
~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.de import GermanLexicon

   lexicon = GermanLexicon(strip_stress=False)

   phonemes = lexicon.lookup("Haus")
   print(phonemes)  # haʊ̯s

   print(f"Dictionary has {len(lexicon):,} entries")  # 738,427

Phoneme Utilities
-----------------

Validation
~~~~~~~~~~

Validate phonemes against Kokoro vocabulary:

.. code-block:: python

   from kokorog2p import validate_phonemes, get_vocab

   # Check if phonemes are valid
   valid = validate_phonemes("hˈɛlO")
   print(valid)  # True

   invalid = validate_phonemes("xyz123")
   print(invalid)  # False

   # Get the full vocabulary
   vocab = get_vocab("us")
   print(f"US vocabulary: {len(vocab)} phonemes")

Conversion
~~~~~~~~~~

Convert between different phoneme formats:

.. code-block:: python

   from kokorog2p import from_espeak, to_espeak

   # Convert espeak IPA to Kokoro
   espeak_ipa = "həlˈəʊ"
   kokoro_phonemes = from_espeak(espeak_ipa, variant="us")
   print(kokoro_phonemes)  # hˈɛlO

   # Convert Kokoro to espeak IPA
   kokoro = "hˈɛlO"
   espeak = to_espeak(kokoro, variant="us")
   print(espeak)

Vocabulary Encoding
-------------------

Convert phonemes to IDs for model input:

.. code-block:: python

   from kokorog2p import phonemes_to_ids, ids_to_phonemes

   # Encode phonemes
   phonemes = "hˈɛlO wˈɜɹld"
   ids = phonemes_to_ids(phonemes)
   print(ids)  # [12, 45, 23, ...]

   # Decode back
   decoded = ids_to_phonemes(ids)
   print(decoded)  # hˈɛlO wˈɜɹld

   # Get Kokoro vocabulary
   from kokorog2p import get_kokoro_vocab
   vocab = get_kokoro_vocab()
   print(f"Kokoro has {len(vocab)} tokens")

Punctuation Handling
--------------------

Automatic Normalization
~~~~~~~~~~~~~~~~~~~~~~~

kokorog2p automatically normalizes punctuation variants to ensure consistency with Kokoro TTS vocabulary:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p("en-us")

   # Ellipsis variants → single ellipsis character (…)
   tokens = g2p("Wait... really?")      # ... → …
   tokens = g2p("Wait. . . really?")    # . . . → …
   tokens = g2p("Wait.. really?")       # .. → …
   tokens = g2p("Wait…really?")         # … preserved

   # Dash variants → em dash (—)
   tokens = g2p("Wait - what?")         # spaced hyphen → em dash
   tokens = g2p("Wait -- what?")        # double hyphen → em dash
   tokens = g2p("Wait – what?")         # en dash → em dash
   tokens = g2p("Wait — what?")         # em dash preserved
   tokens = g2p("Wait ― what?")         # horizontal bar → em dash
   tokens = g2p("Wait ‒ what?")         # figure dash → em dash
   tokens = g2p("Wait − what?")         # minus sign → em dash

   # Compound words preserve hyphens (no normalization)
   tokens = g2p("well-known")           # hyphen removed, words joined
   tokens = g2p("state-of-the-art")     # hyphens removed, words joined

**Normalization Rules:**

* **Ellipsis**: All variants (``...``, ``. . .``, ``..``, ``....``) → ``…`` (U+2026)
* **Em dash**: All dash types when spaced (``-``, ``--``, ``–``, ``—``, ``―``, ``‒``, ``−``) → ``—`` (U+2014)
* **Hyphens in compound words**: Preserved during tokenization, then removed in phoneme output
* **Apostrophes**: All variants (``'``, ``'``, ``'``, ````, ``´``, etc.) → ``'`` (U+0027)

Manual Normalization
~~~~~~~~~~~~~~~~~~~~

Control punctuation normalization manually:

.. code-block:: python

   from kokorog2p import normalize_punctuation, filter_punctuation

   # Normalize to Kokoro punctuation
   text = "Hello... world!!!"
   normalized = normalize_punctuation(text)
   print(normalized)  # Hello. world!

   # Filter out non-Kokoro punctuation
   phonemes = "hˈɛlO… wˈɜɹld‼"
   filtered = filter_punctuation(phonemes)
   print(filtered)  # hˈɛlO. wˈɜɹld!

   # Check if punctuation is valid
   from kokorog2p import is_kokoro_punctuation
   print(is_kokoro_punctuation("!"))   # True
   print(is_kokoro_punctuation("…"))   # True (normalized automatically)
   print(is_kokoro_punctuation("‼"))   # False

Word Mismatch Detection
-----------------------

Detect mismatches between input text and phoneme output:

.. code-block:: python

   from kokorog2p import detect_mismatches

   text = "Hello world!"
   phonemes = "hɛlO wɜɹld !"

   mismatches = detect_mismatches(text, phonemes)

   for mismatch in mismatches:
       print(f"Position {mismatch.position}:")
       print(f"  Input word: {mismatch.input_word}")
       print(f"  Output word: {mismatch.output_word}")
       print(f"  Type: {mismatch.type}")

Number Expansion
----------------

Customize number handling:

English
~~~~~~~

.. code-block:: python

   from kokorog2p.en.numbers import EnglishNumberConverter

   converter = EnglishNumberConverter()

   # Cardinals
   print(converter.convert_cardinal("42"))
   # → forty-two

   # Ordinals
   print(converter.convert_ordinal("42"))
   # → forty-second

   # Years
   print(converter.convert_year("1984"))
   # → nineteen eighty-four

   # Currency
   print(converter.convert_currency("12.50", "$"))
   # → twelve dollars and fifty cents

   # Decimals
   print(converter.convert_decimal("3.14"))
   # → three point one four

German
~~~~~~

.. code-block:: python

   from kokorog2p.de.numbers import GermanNumberConverter

   converter = GermanNumberConverter()

   # Cardinals
   print(converter.convert_cardinal("42"))
   # → zweiundvierzig

   # Ordinals
   print(converter.convert_ordinal("42"))
   # → zweiundvierzigste

   # Years
   print(converter.convert_year("1984"))
   # → neunzehnhundertvierundachtzig

   # Currency
   print(converter.convert_currency("12,50", "€"))
   # → zwölf Euro fünfzig

Custom Backend Selection
-------------------------

Choose specific backends:

.. code-block:: python

   from kokorog2p import get_g2p

   # Use espeak backend
   g2p_espeak = get_g2p("en-us", backend="espeak")

   # Use goruut backend (if installed)
   g2p_goruut = get_g2p("en-us", backend="goruut")

Direct Backend Access
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.backends.espeak import EspeakBackend

   # Create espeak backend
   backend = EspeakBackend(language="en-us")

   # Phonemize a word
   phonemes = backend.phonemize("hello")
   print(phonemes)

Caching and Performance
-----------------------

Managing Cache
~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p import get_g2p, clear_cache

   # G2P instances are cached by language and settings
   g2p1 = get_g2p("en-us", use_spacy=True)
   g2p2 = get_g2p("en-us", use_spacy=True)
   assert g2p1 is g2p2  # Same instance

   # Different settings = different cache entry
   g2p3 = get_g2p("en-us", use_spacy=False)
   assert g2p1 is not g2p3  # Different instance

   # load_silver and load_gold also affect caching
   g2p4 = get_g2p("en-us", load_silver=False)
   assert g2p1 is not g2p4  # Different instance (different silver setting)

   g2p5 = get_g2p("en-us", load_gold=False)
   assert g2p1 is not g2p5  # Different instance (different gold setting)

   # Clear cache when needed
   clear_cache()

Batch Processing
~~~~~~~~~~~~~~~~

For best performance when processing many texts:

.. code-block:: python

   from kokorog2p import get_g2p

   # Create instance once
   g2p = get_g2p("en-us")

   texts = ["Hello", "World", "This", "Is", "Fast"]

   # Process many texts with same instance
   all_tokens = []
   for text in texts:
       tokens = g2p(text)
       all_tokens.append(tokens)

Custom Phoneme Filtering
-------------------------

Filter phonemes for specific use cases:

.. code-block:: python

   from kokorog2p import get_g2p, validate_for_kokoro, filter_for_kokoro

   g2p = get_g2p("en-us")
   tokens = g2p("Hello world!")

   phoneme_str = " ".join(t.phonemes for t in tokens if t.phonemes)

   # Validate for Kokoro
   is_valid = validate_for_kokoro(phoneme_str)

   # Filter to keep only valid Kokoro phonemes
   filtered = filter_for_kokoro(phoneme_str)
   print(filtered)

Mixed-Language Processing
-------------------------

Advanced mixed-language detection and handling.

Direct API Usage
~~~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.mixed_language_g2p import MixedLanguageG2P

   # Create instance with custom configuration
   g2p = MixedLanguageG2P(
       primary_language="de",
       allowed_languages=["de", "en-us", "fr"],
       confidence_threshold=0.6,  # More aggressive detection
       enable_detection=True
   )

   # Process text
   tokens = g2p("Hello, mein Freund! Bonjour!")

   # Access detection metadata
   for token in tokens:
       if token.is_word:
           detected = token.get("detected_language")
           confidence = token.get("language_confidence")
           print(f"{token.text}: {detected} (conf: {confidence:.2f})")

Confidence Tuning
~~~~~~~~~~~~~~~~~

Adjust detection sensitivity based on your use case:

.. code-block:: python

   from kokorog2p import get_g2p

   # Conservative (fewer false positives, may miss some foreign words)
   g2p_conservative = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"],
       language_confidence_threshold=0.9
   )

   # Balanced (recommended default)
   g2p_balanced = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"],
       language_confidence_threshold=0.7  # Default
   )

   # Aggressive (more detections, may have false positives)
   g2p_aggressive = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"],
       language_confidence_threshold=0.5
   )

   # Test on ambiguous text
   text = "Das ist ein Test mit Meeting und Termin."

   for name, g2p_instance in [
       ("Conservative", g2p_conservative),
       ("Balanced", g2p_balanced),
       ("Aggressive", g2p_aggressive)
   ]:
       print(f"\n{name}:")
       tokens = g2p_instance(text)
       for tok in tokens:
           if tok.is_word:
               lang = tok.get("detected_language")
               print(f"  {tok.text} → {lang}")

Multi-Language Support
~~~~~~~~~~~~~~~~~~~~~~

Handle texts mixing more than two languages:

.. code-block:: python

   from kokorog2p import get_g2p

   # Technical documentation mixing French, English, and German
   g2p = get_g2p(
       language="fr",
       multilingual_mode=True,
       allowed_languages=["fr", "en-us", "de"]
   )

   text = """
   Le système utilise un API REST.
   Die Konfiguration ist dans le fichier settings.
   """

   tokens = g2p(text)

   # Group by detected language
   by_language = {}
   for tok in tokens:
       if tok.is_word:
           lang = tok.get("detected_language", "unknown")
           if lang not in by_language:
               by_language[lang] = []
           by_language[lang].append(tok.text)

   for lang, words in by_language.items():
       print(f"{lang}: {', '.join(words)}")

Cache Analysis
~~~~~~~~~~~~~~

Monitor and manage detection cache:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"]
   )

   # Process some texts
   texts = [
       "Hello World",
       "Hallo Welt",
       "The Meeting ist wichtig",
       "Das Projekt is great"
   ]

   for text in texts:
       g2p(text)

   # Check cache size
   cache_size = g2p.get_cache_size()
   print(f"Cache contains {cache_size} unique words")

   # Clear cache for memory management
   if cache_size > 10000:
       g2p.clear_detection_cache()
       print("Cache cleared")

Batch Processing
~~~~~~~~~~~~~~~~

Efficient processing of many mixed-language texts:

.. code-block:: python

   from kokorog2p import get_g2p

   # Create instance once
   g2p = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"]
   )

   # Process many documents
   documents = [
       "Das Meeting beginnt um 10 Uhr.",
       "Please send the Report heute Abend.",
       "Der Workflow ist optimal.",
       # ... many more documents
   ]

   results = []
   for doc in documents:
       phonemes = g2p.phonemize(doc)
       results.append(phonemes)

   # Cache builds up automatically
   print(f"Cached {g2p.get_cache_size()} detections")

Detection Statistics
~~~~~~~~~~~~~~~~~~~~

Analyze detection patterns in your text:

.. code-block:: python

   from kokorog2p import get_g2p
   from collections import Counter

   g2p = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us", "fr"]
   )

   text = """
   Die Präsentation war excellent!
   The Analyse zeigt interessante Résultats.
   Wir müssen das Strategy überdenken.
   """

   tokens = g2p(text)

   # Count words by detected language
   language_counts = Counter()
   low_confidence = []

   for tok in tokens:
       if tok.is_word:
           lang = tok.get("detected_language")
           conf = tok.get("language_confidence", 0)

           language_counts[lang] += 1

           if conf < 0.8:
               low_confidence.append((tok.text, lang, conf))

   print("Language distribution:")
   for lang, count in language_counts.items():
       print(f"  {lang}: {count} words")

   print("\nLow confidence detections:")
   for word, lang, conf in low_confidence:
       print(f"  {word} ({lang}): {conf:.2f}")

Fallback Handling
~~~~~~~~~~~~~~~~~

Handle cases where lingua-py is not available:

.. code-block:: python

   from kokorog2p import get_g2p

   # This will work even without lingua-py
   # Falls back to primary language only
   g2p = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"]
   )

   # Check if detection is actually enabled
   if hasattr(g2p, 'detector') and g2p.detector is not None:
       print("Using automatic language detection")
   else:
       print("Using primary language only (lingua-py not available)")
       print("Install with: pip install kokorog2p[mixed]")

Custom Language Hints
~~~~~~~~~~~~~~~~~~~~~

Provide hints for specific words:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"]
   )

   # Process with token metadata
   tokens = g2p("Das Meeting ist wichtig")

   # You can manually override detection by modifying token metadata
   for tok in tokens:
       if tok.text == "Meeting":
           # Force English pronunciation even if detected as German
           tok.phonemes = "mˈiɾɪŋ"
           tok["detected_language"] = "en-us"

Integration with Markdown
~~~~~~~~~~~~~~~~~~~~~~~~~

Combine with markdown phoneme annotations:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p(
       language="de",
       multilingual_mode=True,
       allowed_languages=["de", "en-us"]
   )

   # Markdown overrides automatic detection
   text = "Das {Meeting|ˈmiːtɪŋ} ist wichtig"

   tokens = g2p(text)
   for tok in tokens:
       if tok.is_word:
           source = tok.get("rating", 0)
           if source == 5:
               print(f"{tok.text}: user-provided → {tok.phonemes}")
           else:
               lang = tok.get("detected_language")
               print(f"{tok.text}: detected ({lang}) → {tok.phonemes}")

Error Handling
--------------

Handle missing dependencies gracefully:

.. code-block:: python

   from kokorog2p import get_g2p

   try:
       # This might fail if Chinese dependencies not installed
       g2p = get_g2p("zh")
       tokens = g2p("你好")
   except ImportError as e:
       print(f"Missing dependency: {e}")
       print("Install with: pip install kokorog2p[zh]")

   try:
       # This might fail if spaCy model not downloaded
       g2p = get_g2p("en-us", use_spacy=True)
   except OSError as e:
       print("spaCy model not found")
       print("Download with: python -m spacy download en_core_web_sm")

Next Steps
----------

* See :doc:`api/core` for detailed API reference
* Check :doc:`languages` for language-specific features
* Read :doc:`phonemes` to understand the phoneme inventory
