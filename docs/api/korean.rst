Korean API
==========

Korean G2P provides phoneme conversion using MeCab for morphological analysis and custom phonological rules based on Korean Standard Pronunciation.

Main Class
----------

.. autoclass:: kokorog2p.ko.KoreanG2P
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

.. code-block:: python

   from kokorog2p.ko import KoreanG2P

   g2p = KoreanG2P(language="ko-kr")
   tokens = g2p("안녕하세요!")

   for token in tokens:
       print(f"{token.text} -> {token.phonemes}")

Implementation
--------------

The Korean G2P implementation is based on g2pK by kyubyong and uses:

- MeCab for morphological analysis
- Korean Standard Pronunciation rules
- Jamo-to-IPA conversion for phoneme output

Reference: https://github.com/kyubyong/g2pK
