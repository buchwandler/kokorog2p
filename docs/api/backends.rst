Backends API
============

kokorog2p supports multiple phonemization backends.

espeak-ng Backend
-----------------

.. autoclass:: kokorog2p.backends.espeak.EspeakBackend
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: kokorog2p.espeak_g2p.EspeakOnlyG2P
   :members:
   :undoc-members:
   :show-inheritance:

goruut Backend
--------------

.. autoclass:: kokorog2p.goruut_g2p.GoruutOnlyG2P
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

espeak Backend
~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.backends.espeak import EspeakBackend

   backend = EspeakBackend(language="en-us")
   phonemes = backend.phonemize("hello")
   print(phonemes)

Using espeak-only G2P
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.espeak_g2p import EspeakOnlyG2P

   # Strict mode (default) - raises errors if espeak fails
   g2p = EspeakOnlyG2P(language="es-es", strict=True)
   tokens = g2p("Hola mundo")

   for token in tokens:
       print(f"{token.text} -> {token.phonemes}")

   # Lenient mode - returns empty on errors (backward compatible)
   g2p_lenient = EspeakOnlyG2P(language="es-es", strict=False)
   tokens = g2p_lenient("Hola mundo")

Using goruut Backend
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   from kokorog2p.goruut_g2p import GoruutOnlyG2P

   # Strict mode (default)
   g2p = GoruutOnlyG2P(language="en-us", strict=True)
   tokens = g2p("Hello world")

   for token in tokens:
       print(f"{token.text} -> {token.phonemes}")

   # Lenient mode
   g2p_lenient = GoruutOnlyG2P(language="en-us", strict=False)
   tokens = g2p_lenient("Hello world")
