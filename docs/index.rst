Welcome to kokorog2p's documentation!
========================================

**kokorog2p** is a unified G2P (Grapheme-to-Phoneme) library for Kokoro TTS, providing high-quality text-to-phoneme conversion for multiple languages.

.. image:: https://img.shields.io/pypi/v/kokorog2p.svg
   :target: https://pypi.org/project/kokorog2p/
   :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/kokorog2p.svg
   :target: https://pypi.org/project/kokorog2p/
   :alt: Python versions

Features
--------

* **Multi-language support**: English (US/GB), German, French, Czech, Spanish, Italian, Portuguese, Chinese, Japanese, Korean, Hebrew
* **Mixed-language detection**: Automatic detection and handling of texts mixing multiple languages
* **Dictionary-based lookup** with large gold/silver tier lexicons for select languages
* **Rule-based G2P** for Romance and Slavic languages with comprehensive phonological rules
* **espeak-ng integration** as a fallback for out-of-vocabulary words
* **Automatic IPA to Kokoro phoneme conversion**
* **Number and currency handling** across all languages
* **Stress assignment** based on linguistic rules
* **High performance** with caching and optimized lookup

Quick Start
-----------

.. code-block:: python

   from kokorog2p import phonemize

   # English
   phonemes = phonemize("Hello world!", language="en-us")
   print(phonemes)  # hˈɛlO wˈɜɹld!

   # German
   phonemes = phonemize("Guten Tag", language="de")
   print(phonemes)  # ɡuːtn̩ taːk

   # French
   phonemes = phonemize("Bonjour", language="fr")
   print(phonemes)  # bɔ̃ʒuʁ

Installation
------------

.. code-block:: bash

   # Core package
   pip install kokorog2p

   # With English support (includes spaCy)
   pip install kokorog2p[en]

   # With espeak-ng backend
   pip install kokorog2p[espeak]

   # Full installation (all languages and backends)
   pip install kokorog2p[all]

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   languages
   advanced
   abbreviation_customization
   phonemes

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/english
   api/german
   api/french
   api/czech
   api/spanish
   api/italian
   api/portuguese
   api/chinese
   api/japanese
   api/korean
   api/hebrew
   api/mixed
   api/backends
   api/utils

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
