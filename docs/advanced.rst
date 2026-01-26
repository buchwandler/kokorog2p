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

* **5**: User-provided (via OverrideSpan) or gold dictionary (highest quality)
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

Quote Handling
--------------

kokorog2p provides sophisticated quote handling with support for nested quotes and automatic conversion to curly quotes.

Nested Quote Detection
~~~~~~~~~~~~~~~~~~~~~~

The tokenizer supports two modes for handling quotes:

.. code-block:: python

   from kokorog2p import get_g2p

   # Default: Bracket-matching mode (supports nesting)
   g2p = get_g2p("en-us")
   tokens = g2p('He said "She used `backticks` here"')

   # Check quote depths
   for token in tokens:
       depth = token.quote_depth
       print(f"{token.text}: depth={depth}")
   # Output shows nesting: "=1, `=2, `=2, "=1

**Bracket-Matching Mode** (default):

* Supports nested quotes when using **different** quote characters
* Maintains a stack to track nesting depth
* Supported quote characters: ``"`` (double quote), `````` (backtick), ``'`` (single quote)
* Depth increases with each level of nesting (1 = outermost, 2 = nested once, etc.)

**Important**: Nesting only works with different quote types:

* ✅ **Supported**: ``"outer `inner` text"`` → depths ``[1, 2, 2, 1]`` (different quotes)
* ❌ **NOT supported**: ``"level1 "level2""`` → depths ``[1, 1, 1, 1]`` (same quotes alternate)

Examples:

.. code-block:: python

   from kokorog2p.pipeline.tokenizer import RegexTokenizer

   # Create tokenizer with bracket matching (default)
   tokenizer = RegexTokenizer(use_bracket_matching=True)

   # Simple pair
   tokens = tokenizer.tokenize('"hello"', '"hello"')
   # Quote depths: [1, 1]

   # Nested quotes (different types)
   tokens = tokenizer.tokenize('"outer `inner` text"', '"outer `inner` text"')
   # Quote depths: [1, 2, 2, 1]

   # Multiple separate pairs
   tokens = tokenizer.tokenize('"first" and "second"', '"first" and "second"')
   # Quote depths: [1, 1, 1, 1]

   # Triple nesting (different types)
   tokens = tokenizer.tokenize('"a `b \'c\' d` e"', '"a `b \'c\' d` e"')
   # Quote depths: [1, 2, 3, 3, 2, 1]

**Simple Alternation Mode**:

For simpler use cases without nesting support:

.. code-block:: python

   from kokorog2p.pipeline.tokenizer import RegexTokenizer

   # Disable bracket matching for simple alternation
   tokenizer = RegexTokenizer(use_bracket_matching=False)

   # First quote opens (depth 1), second closes (depth 0)
   tokens = tokenizer.tokenize('"hello" world', '"hello" world')
   # Quote depths: [1, 0, 0]

Curly Quote Conversion
~~~~~~~~~~~~~~~~~~~~~~

The tokenizer automatically converts straight quotes to curly quotes based on nesting depth:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p("en-us")

   # Straight quotes converted to curly quotes
   tokens = g2p('She said "hello"')

   # First quote becomes left curly ("), last becomes right curly (")
   quote_chars = [t.text for t in tokens if t.text in ('"', '"')]
   print(quote_chars)  # ['"', '"']

**Conversion Rules**:

* Opening quotes (depth increases) → left curly quote ``"`` (U+201C)
* Closing quotes (depth decreases) → right curly quote ``"`` (U+201D)
* Backticks follow the same pattern as double quotes
* Single quotes use standard apostrophe ``'`` (U+0027)

Quote Depth in Custom Processing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Access quote depth for custom processing:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p("en-us")
   tokens = g2p('He said "She whispered `quietly`"')

   # Analyze quote nesting
   for token in tokens:
       if token.quote_depth > 0:
           indent = "  " * (token.quote_depth - 1)
           print(f"{indent}[{token.quote_depth}] {token.text}")

Output shows nesting structure:

.. code-block:: text

   [1] "
   [1] She
   [1] whispered
     [2] `
     [2] quietly
     [2] `
   [1] "

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

Multilang Preprocessing
------------------------

Use ``preprocess_multilang`` to get language override spans for mixed-language text.
This integrates with the span-based phonemization API.

.. code-block:: python

   from kokorog2p import phonemize
   from kokorog2p.multilang import preprocess_multilang

   text = "Hello, mein Freund! Bonjour!"
   overrides = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us", "fr"],
       confidence_threshold=0.6,
   )

   result = phonemize(text, language="de", overrides=overrides)

Confidence Tuning
~~~~~~~~~~~~~~~~~

Adjust detection sensitivity based on your use case:

.. code-block:: python

   from kokorog2p.multilang import preprocess_multilang

   text = "Das Meeting ist wichtig"

   conservative = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us"],
       confidence_threshold=0.9,
   )

   aggressive = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us"],
       confidence_threshold=0.5,
   )

Integration with Span API
~~~~~~~~~~~~~~~~~~~~~~~~~~

Combine language detection with other span overrides:

.. code-block:: python

   from kokorog2p import phonemize, OverrideSpan
   from kokorog2p.multilang import preprocess_multilang

   text = "Das Meeting ist wichtig"

   # Get language overrides
   lang_overrides = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us"],
   )

   # Add custom phoneme override
   all_overrides = lang_overrides + [
       OverrideSpan(4, 11, {"ph": "ˈmiːtɪŋ"})  # Custom pronunciation for "Meeting"
   ]

   result = phonemize(text, language="de", overrides=all_overrides)


Error Handling
--------------

kokorog2p provides robust error handling to help you debug issues, especially in CI/CD environments.

Strict Mode (Default)
~~~~~~~~~~~~~~~~~~~~~

By default, kokorog2p uses **strict mode** (``strict=True``), which raises clear exceptions when backend initialization or phonemization fails:

.. code-block:: python

   from kokorog2p import get_g2p

   # Strict mode is the default
   g2p = get_g2p("en-us", backend="espeak", strict=True)

   try:
       result = g2p.phonemize("test")
   except RuntimeError as e:
       # Get detailed error message about what went wrong
       print(f"Error: {e}")
       # Example: "Espeak backend validation failed. Please ensure espeak-ng
       # is properly installed and voice 'en-us' is available."

**Benefits of strict mode:**

* Catches configuration issues immediately
* Provides actionable error messages
* Prevents silent failures in CI/CD pipelines
* Recommended for production use

Lenient Mode (Backward Compatible)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For backward compatibility with older versions (< 0.4.0) that silently failed, you can use **lenient mode** (``strict=False``):

.. code-block:: python

   from kokorog2p import get_g2p

   # Lenient mode logs errors but doesn't raise exceptions
   g2p = get_g2p("en-us", backend="espeak", strict=False)

   result = g2p.phonemize("test")
   # If espeak fails:
   # - Error is logged to Python's logging system
   # - Returns empty string "" instead of raising exception
   # - Allows your application to continue running

**When to use lenient mode:**

* Migrating from older versions (< 0.4.0)
* Non-critical applications where empty results are acceptable
* When you have your own error handling logic

Common Error Scenarios
~~~~~~~~~~~~~~~~~~~~~~

**espeak-ng not installed:**

.. code-block:: python

   # Strict mode (default)
   g2p = get_g2p("en-us", backend="espeak")
   # RuntimeError: Espeak backend validation failed. Please ensure espeak-ng
   # is properly installed...

   # Solution: Install espeak-ng
   # Ubuntu/Debian: sudo apt-get install espeak-ng
   # macOS: brew install espeak
   # Windows: Download from https://github.com/espeak-ng/espeak-ng/releases

**Invalid voice:**

.. code-block:: python

   from kokorog2p.espeak_g2p import EspeakOnlyG2P

   g2p = EspeakOnlyG2P(language="xx-invalid")
   # RuntimeError: Espeak backend validation failed...voice 'xx-invalid' is unavailable

**CI/CD Best Practices:**

.. code-block:: python

   import logging

   # Configure logging to see error details
   logging.basicConfig(level=logging.INFO)

   # Use strict mode in CI to catch issues early (this is the default)
   g2p = get_g2p("en-us", backend="espeak", strict=True)

   # Your CI will fail with clear error messages if there are issues

**Handling missing dependencies:**

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

Configuring with Different Backends
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``strict`` parameter works with all backends:

.. code-block:: python

   from kokorog2p import get_g2p

   # Espeak backend with strict mode
   g2p_espeak = get_g2p("en-us", backend="espeak", strict=True)

   # Goruut backend with strict mode
   g2p_goruut = get_g2p("en-us", backend="goruut", strict=True)

   # Dictionary-based with fallback (strict controls fallback/init errors)
   g2p_dict = get_g2p(
       "en-us",
       backend="kokorog2p",
       use_espeak_fallback=True,
       strict=True  # Affects fallback initialization and errors
   )

Next Steps
----------

* See :doc:`api/core` for detailed API reference
* Check :doc:`languages` for language-specific features
* Read :doc:`phonemes` to understand the phoneme inventory
