Hebrew API
==========

Hebrew G2P provides phoneme conversion using the phonikud package for handling Hebrew text with diacritics (nikud).

Main Class
----------

.. autoclass:: kokorog2p.he.HebrewG2P
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

.. code-block:: python

   from kokorog2p.he import HebrewG2P

   g2p = HebrewG2P(language="he-il")
   tokens = g2p("שלום עולם!")

   for token in tokens:
       print(f"{token.text} -> {token.phonemes}")

Implementation
--------------

The Hebrew G2P implementation uses the phonikud package which:

- Handles Hebrew text with diacritics (nikud)
- Converts Hebrew to IPA phoneme representation
- Supports both modern and biblical Hebrew

Reference: https://github.com/thewh1teagle/phonikud
