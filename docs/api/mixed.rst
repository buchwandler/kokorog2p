SSMD Multilang Preprocessing
============================

The multilang preprocessor detects word-level languages with
``lingua-language-detector`` and adds SSMD ``{lang="..."}`` annotations.
It is intentionally separate from ``get_g2p``; users call it explicitly
before SSMD phonemization.

API
---

.. autofunction:: kokorog2p.multilang.preprocess_multilang

Examples
--------

Basic Usage
~~~~~~~~~~~

.. code-block:: python

   from kokorog2p import get_g2p, phonemize_with_ssmd
   from kokorog2p.multilang import preprocess_multilang

   text = "Schöne World"
   annotated = preprocess_multilang(
       text,
       default_language="en-us",
       allowed_languages=["en-us", "de"],
   )

   g2p = get_g2p("en-us", use_ssmd=True)
   result = g2p.phonemize(annotated)

Confidence Tuning
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.multilang import preprocess_multilang

   annotated = preprocess_multilang(
       "Bonjour World",
       default_language="en-us",
       allowed_languages=["en-us", "fr"],
       confidence_threshold=0.5,
   )
