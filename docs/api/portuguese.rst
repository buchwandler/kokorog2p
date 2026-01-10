Portuguese API
==============

Portuguese G2P provides rule-based phoneme conversion for Brazilian Portuguese, designed for Kokoro TTS models.

Main Class
----------

.. autoclass:: kokorog2p.pt.PortugueseG2P
   :members:
   :undoc-members:
   :show-inheritance:

Examples
--------

.. code-block:: python

   from kokorog2p.pt import PortugueseG2P

   g2p = PortugueseG2P(language="pt-br")
   tokens = g2p("Olá mundo!")

   for token in tokens:
       print(f"{token.text} -> {token.phonemes}")

Phonology Features
------------------

Brazilian Portuguese phonology includes:

- 7 oral vowels (a, e, ɛ, i, o, ɔ, u) with open/closed e/o variants
- 5 nasal vowels (ã, ẽ, ĩ, õ, ũ)
- Nasal diphthongs (ãw̃, õj̃, etc.)
- Palatalization: lh [ʎ], nh [ɲ], x/ch [ʃ]
- Affrication: t+i [ʧ], d+i [ʤ] (Brazilian Portuguese feature)
- Sibilants: s [s/z], x [ʃ], z [z]
- Liquids: r [ʁ/x/h] (varies by dialect), rr [ʁ/x], single r [ɾ]
- No θ sound (unlike European Portuguese)
