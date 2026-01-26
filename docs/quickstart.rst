Quick Start
===========

This guide will help you get started with kokorog2p quickly.

Basic Usage
-----------

The simplest way to use kokorog2p is with the ``phonemize()`` function:

.. code-block:: python

   from kokorog2p import phonemize

   # Convert text to phonemes
   phonemes = phonemize("Hello world!")
   print(phonemes)  # hˈɛlO wˈɜɹld!

Error Handling
--------------

By default, kokorog2p raises clear errors when backends fail (v0.4.0+):

.. code-block:: python

   from kokorog2p import get_g2p

   # Strict mode (default) - raises errors
   try:
       g2p = get_g2p("en-us", backend="espeak")
       tokens = g2p("Hello world!")
   except RuntimeError as e:
       print(f"Error: {e}")
       # Will show helpful message if espeak-ng is not installed

   # Lenient mode - returns empty strings on errors (backward compatible)
   g2p = get_g2p("en-us", backend="espeak", strict=False)
   tokens = g2p("Hello world!")  # Returns empty strings if backend fails

For more details, see :doc:`advanced`.

Specifying Language
-------------------

You can specify the language explicitly:

.. code-block:: python

   from kokorog2p import phonemize

   # US English (default)
   us_phonemes = phonemize("Hello world!", language="en-us")

   # British English
   gb_phonemes = phonemize("Hello world!", language="en-gb")

   # German
   de_phonemes = phonemize("Guten Tag", language="de")

   # French
   fr_phonemes = phonemize("Bonjour le monde", language="fr")

   # Czech
   cs_phonemes = phonemize("Dobrý den", language="cs")

   # Mixed-language (German with English words)
   from kokorog2p import phonemize
   from kokorog2p.multilang import preprocess_multilang

   text = "Das Meeting war great!"
   overrides = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us"],
   )
   mixed_phonemes = phonemize(text, lang="de", overrides=overrides,
                      resturn_type="phonemes")

Using G2P Instances
-------------------

For more control, create a G2P instance:

.. code-block:: python

   from kokorog2p import get_g2p

   # Get a G2P instance for US English
   g2p = get_g2p("en-us")

   # Convert text
   tokens = g2p("The quick brown fox jumps over the lazy dog.")

   # Access individual tokens
   for token in tokens:
       print(f"{token.text:15} → {token.phonemes}")

Output:

.. code-block:: text

   The             → ðə
   quick           → kwˈɪk
   brown           → bɹˈaʊn
   fox             → fˈɑks
   jumps           → dʒˈʌmps
   over            → ˈOvɚ
   the             → ðə
   lazy            → lˈeɪzi
   dog             → dˈɔɡ
   .               → .

Language-Specific G2P
---------------------

You can also import language-specific G2P classes:

English
~~~~~~~

.. code-block:: python

   from kokorog2p.en import EnglishG2P

   g2p = EnglishG2P(
       language="en-us",
       use_espeak_fallback=True,
       use_spacy=True
   )

   tokens = g2p("I can't believe it!")
   for token in tokens:
       print(f"{token.text} → {token.phonemes} (tag: {token.tag})")

German
~~~~~~

.. code-block:: python

   from kokorog2p.de import GermanG2P

   g2p = GermanG2P(
       language="de-de",
       use_espeak_fallback=True
   )

   tokens = g2p("Wie geht es Ihnen?")
   for token in tokens:
       print(f"{token.text} → {token.phonemes}")

French
~~~~~~

.. code-block:: python

   from kokorog2p.fr import FrenchG2P

   g2p = FrenchG2P(
       language="fr-fr",
       use_espeak_fallback=True
   )

   tokens = g2p("Comment allez-vous?")
   for token in tokens:
       print(f"{token.text} → {token.phonemes}")

Czech
~~~~~

.. code-block:: python

   from kokorog2p.cs import CzechG2P

   g2p = CzechG2P(language="cs-cz")

   tokens = g2p("Jak se máte?")
   for token in tokens:
       print(f"{token.text} → {token.phonemes}")

Mixed-Language
~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize
   from kokorog2p.multilang import preprocess_multilang

   text = "Das Meeting war great!"
   overrides = preprocess_multilang(
       text,
       default_language="de",
       allowed_languages=["de", "en-us"],
   )
   result = phonemize(text, language="de", overrides=overrides)

   for token in result.tokens:
       print(f"{token.text} ({token.lang}) → {token.phonemes}")

Output:

.. code-block:: text

   Das (de) → das
   Meeting (en-us) → mˈiɾɪŋ
   war (de) → vaːɐ̯
   great (en-us) → ɡɹˈeɪt

Working with Tokens
-------------------

Tokens contain rich information:

.. code-block:: python

   from kokorog2p import get_g2p

   g2p = get_g2p("en-us", use_spacy=True)
   tokens = g2p("I love reading!")

   for token in tokens:
       print(f"Text:      {token.text}")
       print(f"Phonemes:  {token.phonemes}")
       print(f"POS tag:   {token.tag}")
       print(f"Rating:    {token.get('rating')}")
       print(f"Whitespace: '{token.whitespace}'")
       print("---")

Output:

.. code-block:: text

   Text:      I
   Phonemes:  ˈaɪ
   POS tag:   PRP
   Rating:    5
   Whitespace: ' '
   ---
   Text:      love
   Phonemes:  lˈʌv
   POS tag:   VBP
   Rating:    5
   Whitespace: ' '
   ---

Number Handling
---------------

kokorog2p automatically handles numbers:

.. code-block:: python

   from kokorog2p import phonemize

   # Numbers
   print(phonemize("I have 42 apples.", language="en-us"))
   # → aɪ hæv fˈOɹti tˈu ˈæpəlz.

   # Currency
   print(phonemize("It costs $12.50", language="en-us"))
   # → ɪt kˈɑsts twˈɛlv dˈɑlɚz ænd fˈɪfti sˈɛnts

   # German numbers
   print(phonemize("Ich habe 42 Äpfel.", language="de"))
   # → ɪç haːbə t͡svaɪ̯ʊntfɪɐ̯t͡sɪç ɛːpfl̩.

Choosing Backends
-----------------

You can choose different phonemization backends:

espeak Backend (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   # Uses espeak-ng for fallback
   result = phonemize("Hello", backend="espeak")

goruut Backend
~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize

   # Uses goruut (if installed)
   result = phonemize("Hello", backend="goruut")

Disabling Fallback
------------------

You can disable fallback for out-of-vocabulary words:

.. code-block:: python

   from kokorog2p import get_g2p

   # No fallback - unknown words will have empty phonemes
   g2p = get_g2p("en-us", use_espeak_fallback=False)

   tokens = g2p("xyznotaword")
   print(tokens[0].phonemes)  # Will be empty or "?"

Performance Tips
----------------

1. **Reuse G2P instances**: Creating instances is expensive

   .. code-block:: python

      # Good: Reuse the same instance
      g2p = get_g2p("en-us")
      for text in texts:
          tokens = g2p(text)

      # Bad: Create new instance each time
      for text in texts:
          g2p = get_g2p("en-us")  # Slow!
          tokens = g2p(text)

2. **Use caching**: G2P instances are cached by default

   .. code-block:: python

      # These return the same cached instance
      g2p1 = get_g2p("en-us")
      g2p2 = get_g2p("en-us")
      assert g2p1 is g2p2

3. **Clear cache when needed**:

   .. code-block:: python

      from kokorog2p import clear_cache

      # Clear all cached instances
      clear_cache()

Next Steps
----------

* Learn about :doc:`languages` for language-specific features
* See :doc:`advanced` for advanced usage patterns
* Check the :doc:`api/core` for detailed API documentation
