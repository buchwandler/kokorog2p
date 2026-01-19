Multilang Preprocessing
============================

The multilang preprocessor detects word-level languages with
``lingua-language-detector`` and returns ``OverrideSpan`` objects for
language switching. It integrates with the span-based phonemization API.

API
---

.. autofunction:: kokorog2p.multilang.preprocess_multilang

Examples
--------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from kokorog2p import phonemize_to_result
   from kokorog2p.multilang import preprocess_multilang

   text = "Schöne World"
   overrides = preprocess_multilang(
       text,
       default_language="en-us",
       allowed_languages=["en-us", "de"],
   )

   result = phonemize_to_result(text, lang="en-us", overrides=overrides)

Confidence Tuning
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.multilang import preprocess_multilang

   overrides = preprocess_multilang(
       "Bonjour World",
       default_language="en-us",
       allowed_languages=["en-us", "fr"],
       confidence_threshold=0.5,
   )
