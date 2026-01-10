Italian API
===========

Italian G2P provides rule-based phoneme conversion for Italian, designed for Kokoro TTS models.

Main Class
----------

.. autoclass:: kokorog2p.it.ItalianG2P
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

.. code-block:: python

   from kokorog2p.it import ItalianG2P

   g2p = ItalianG2P(language="it-it")
   tokens = g2p("Ciao mondo!")

   for token in tokens:
       print(f"{token.text} -> {token.phonemes}")

Phonology Features
------------------

Italian phonology includes:

- 5 pure vowels (a, e, i, o, u) - always pronounced clearly
- No vowel reduction (unlike English)
- Predictable stress (usually penultimate syllable)
- Gemination (double consonants) is phonemically distinctive
- Palatals: gn [ɲ], gli [ʎ]
- Affricates: z [ʦ/ʣ], c/ci [ʧ], g/gi [ʤ]
- No diphthongs in standard Italian (consecutive vowels are separate syllables)
