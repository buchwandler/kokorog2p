Chinese API
===========

Chinese G2P uses jieba for tokenization and supports two phoneme output formats.

Main Class
----------

.. autoclass:: kokorog2p.zh.ChineseG2P
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

Basic Usage
^^^^^^^^^^^

.. code-block:: python

   from kokorog2p.zh import ChineseG2P

   g2p = ChineseG2P(language="zh")
   tokens = g2p("你好世界")

   for token in tokens:
       print(f"{token.text} -> {token.phonemes}")

Model Versions
--------------

The Chinese G2P supports two versions with different output formats:

Legacy Version (version="1.0")
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Uses pypinyin + IPA transcription

* Output format: IPA with arrow tone markers (↓ ↗ ↘ →)
* Compatible with base Kokoro model
* Example: ``"你好"`` → ``"ni↓xau↓"``

.. code-block:: python

   from kokorog2p import get_g2p

   # Create legacy Chinese G2P
   g2p = get_g2p("zh", version="1.0")
   phonemes = g2p.phonemize("你好")
   # Output: 'ni↓xau↓'

Version 1.1 (version="1.1")
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Uses ZHFrontend with Zhuyin (Bopomofo) notation

* Output format: Zhuyin characters + tone numbers (1-5)
* Requires Kokoro-82M-v1.1-zh model
* Example: ``"你好"`` → ``"ㄋㄧ2ㄏㄠ3"``

.. code-block:: python

   from kokorog2p import get_g2p
   from kokorog2p.vocab import validate_for_kokoro

   # Create v1.1 Chinese G2P
   g2p = get_g2p("zh", version="1.1")
   phonemes = g2p.phonemize("你好")
   # Output: 'ㄋㄧ2ㄏㄠ3'

   # Validate against v1.1-zh model
   is_valid, invalid = validate_for_kokoro(phonemes, model="1.1")
   assert is_valid

Model Selection for Validation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When validating phonemes, specify the target model:

.. code-block:: python

   from kokorog2p.vocab import validate_for_kokoro

   # For base model (IPA output from legacy version)
   is_valid, invalid = validate_for_kokoro(phonemes, model="1.0")

   # For v1.1-zh model (Zhuyin output from version 1.1)
   is_valid, invalid = validate_for_kokoro(phonemes, model="1.1")

Features
--------

* Jieba tokenization for Chinese word segmentation
* Pypinyin for pinyin conversion to IPA (legacy version)
* ZHFrontend with Zhuyin notation (version 1.1)
* Tone sandhi rules
* cn2an for number handling
* Chinese to Western punctuation mapping
