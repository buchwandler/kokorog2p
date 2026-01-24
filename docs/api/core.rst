Core API
========

This module contains the core functionality of kokorog2p.

Main Functions
--------------

.. autofunction:: kokorog2p.phonemize

.. autofunction:: kokorog2p.tokenize

.. autofunction:: kokorog2p.get_g2p

.. autofunction:: kokorog2p.clear_cache

.. autofunction:: kokorog2p.reset_abbreviations

Base Classes
------------

G2PBase
~~~~~~~

.. autoclass:: kokorog2p.G2PBase
   :members:
   :undoc-members:
   :show-inheritance:

GToken
~~~~~~

.. autoclass:: kokorog2p.GToken
   :members:
   :undoc-members:
   :show-inheritance:

   .. attribute:: text

      The original text of this token.

   .. attribute:: phonemes

      The IPA phoneme string for this token.

   .. attribute:: tag

      Part-of-speech tag (if available).

   .. attribute:: whitespace

      Whitespace following this token.

Phoneme Utilities
-----------------

Vocabulary
~~~~~~~~~~

.. autofunction:: kokorog2p.get_vocab

.. autofunction:: kokorog2p.validate_phonemes

.. autodata:: kokorog2p.US_VOCAB
   :annotation:

.. autodata:: kokorog2p.GB_VOCAB
   :annotation:

.. autodata:: kokorog2p.VOWELS
   :annotation:

.. autodata:: kokorog2p.CONSONANTS
   :annotation:

Conversion
~~~~~~~~~~

.. autofunction:: kokorog2p.from_espeak

.. autofunction:: kokorog2p.from_goruut

.. autofunction:: kokorog2p.to_espeak

Kokoro Vocabulary
-----------------

Encoding/Decoding
~~~~~~~~~~~~~~~~~

.. autofunction:: kokorog2p.encode

.. autofunction:: kokorog2p.decode

.. autofunction:: kokorog2p.phonemes_to_ids

.. autofunction:: kokorog2p.ids_to_phonemes

Validation
~~~~~~~~~~

.. autofunction:: kokorog2p.validate_for_kokoro

.. autofunction:: kokorog2p.filter_for_kokoro

Configuration
~~~~~~~~~~~~~

.. autofunction:: kokorog2p.get_kokoro_vocab

.. autofunction:: kokorog2p.get_kokoro_config

.. autodata:: kokorog2p.N_TOKENS
   :annotation:

.. autodata:: kokorog2p.PAD_IDX
   :annotation:

Punctuation
-----------

.. autoclass:: kokorog2p.Punctuation
   :members:
   :undoc-members:

.. autofunction:: kokorog2p.normalize_punctuation

.. autofunction:: kokorog2p.filter_punctuation

.. autofunction:: kokorog2p.is_kokoro_punctuation

.. autodata:: kokorog2p.KOKORO_PUNCTUATION
   :annotation:

Word Mismatch Detection
-----------------------

.. autoclass:: kokorog2p.MismatchMode
   :members:
   :undoc-members:

.. autoclass:: kokorog2p.MismatchInfo
   :members:
   :undoc-members:

.. autoclass:: kokorog2p.MismatchStats
   :members:
   :undoc-members:

.. autofunction:: kokorog2p.detect_mismatches

.. autofunction:: kokorog2p.check_word_alignment

.. autofunction:: kokorog2p.count_words
