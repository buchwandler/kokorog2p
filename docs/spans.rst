Span-Based Phonemization Guide
===============================

This document explains the span-based (offset-based) phonemization system in kokorog2p, which provides deterministic, pipeline-friendly text-to-phoneme conversion.

Overview
--------

The span-based system uses **character offsets** to precisely identify and override specific portions of text during phonemization. This approach is more robust than word-based matching because it handles:

* **Duplicate words** with different pronunciations (e.g., "the cat the dog")
* **Partial word matches** (e.g., distinguishing "cat" from "category")
* **Complex text structures** with punctuation and whitespace variations
* **Pipeline integration** with offset-preserving preprocessing

Core Types
----------

TokenSpan
~~~~~~~~~

Represents a single token with its phonemization and metadata:

.. code-block:: python

   @dataclass
   class TokenSpan:
       text: str              # Original text ("hello")
       char_start: int        # Character offset start (0)
       char_end: int          # Character offset end (5)
       lang: str | None = None  # Language override ("en-us", "fr", etc.)
       extended_text: str | None = None  # Expanded text for phonemization
       meta: dict[str, Any] = field(default_factory=dict)  # Metadata including phonemes

**Key Properties:**

* ``char_start`` and ``char_end`` are **character offsets** in the clean text (after markup removal)
* ``char_end`` is **exclusive** (Python slice convention: ``text[char_start:char_end]``)
* Multiple tokens can reference the same text position if tokenization creates sub-parts
* Whitespace is inferred from offsets (tokens are words/punctuation only)
* Abbreviations keep trailing periods in the same token (e.g., ``Mr.``)
* ``extended_text`` holds optional expansions (e.g., ``Mr.`` → ``Mister`` or ``1`` → ``one``)
* Phonemes are stored in ``meta["phonemes"]`` after phonemization

**Example:**

.. code-block:: python

   text = "Hello Mr. Smith!"
   tokens = tokenize(text, language="en-us")
   # TokenSpan(text="Hello", char_start=0, char_end=5, ...)
   # TokenSpan(text="Mr.", char_start=6, char_end=9, ...)
   # TokenSpan(text="Smith", char_start=10, char_end=15, ...)
   # TokenSpan(text="!", char_start=15, char_end=16, ...)

OverrideSpan
~~~~~~~~~~~~

Specifies a region of text to override during phonemization:

.. code-block:: python

   @dataclass
   class OverrideSpan:
       char_start: int                 # Character offset start
       char_end: int                   # Character offset end (exclusive)
       attrs: dict[str, str]           # Override attributes

**Common Attributes:**

* ``ph``: Direct phoneme override (e.g., ``{"ph": "həlˈO"}``)
* ``lang``: Language switch (e.g., ``{"lang": "fr"}``)
* Custom attributes for pipeline processing

**Example:**

.. code-block:: python

   text = "the cat the dog"
   overrides = [
       OverrideSpan(0, 3, {"ph": "ðə"}),   # First "the" → /ðə/
       OverrideSpan(8, 11, {"ph": "ði"}),  # Second "the" → /ði/
   ]

PhonemizeResult
~~~~~~~~~~~~~~~

The complete phonemization output:

.. code-block:: python

   @dataclass
   class PhonemizeResult:
       clean_text: str                  # Text with markup removed
       tokens: list[TokenSpan]          # Token-level information with offsets
       extended_text: str               # Expanded text for phonemization
       phonemes: str                    # Concatenated phoneme string
       token_ids: list[int]             # token IDs for model input
       warnings: list[str]              # Alignment warnings

Extended Text Layer
-------------------

Span alignment always uses ``clean_text`` offsets. When abbreviations or numbers
are expanded for phonemization, the expanded form is stored on each token's
``extended_text`` and in ``PhonemizeResult.extended_text``. This keeps character
offsets stable while allowing the phonemizer to speak the expanded form.

Example:

.. code-block:: python

   text = "Meet Mr. Smith"
   result = phonemize(text)
   # TokenSpan(text="Mr.", extended_text="Mister", char_start=5, char_end=8, ...)
   # result.clean_text == "Meet Mr. Smith"
   # result.extended_text == "Meet Mister Smith"

Character Offset Coordinate System
-----------------------------------

Basic Rules
~~~~~~~~~~~

1. **Zero-indexed**: First character is at position ``0``
2. **Exclusive end**: Range ``[start, end)`` means characters from ``start`` up to but not including ``end``
3. **Clean text reference**: Offsets refer to text **after** markup removal but **before** normalization

Examples
~~~~~~~~

.. code-block:: python

   text = "Hello world"
   #       0123456789...

   # "Hello" → char_start=0, char_end=5
   # "world" → char_start=6, char_end=11
   # " " (space) → char_start=5, char_end=6

With Markup
~~~~~~~~~~~

.. code-block:: python

   # Original: "@Hello@ world"  (with marker-based override)
   # Clean text: "Hello world"
   #              0123456789...

   override = OverrideSpan(0, 5, {"ph": "həlˈO"})  # Refers to "Hello" in clean text

Duplicate Words
~~~~~~~~~~~~~~~

.. code-block:: python

   text = "the cat the dog"
   #       012345678901234...

   # First "the" → OverrideSpan(0, 3, ...)
   # Second "the" → OverrideSpan(8, 11, ...)

Alignment Modes
---------------

The system supports two alignment modes for applying overrides to tokens:

1. Span Alignment (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Recommended for all new code.** Uses character offsets for deterministic matching.

**Matching Logic:**

* **Exact match**: Override span exactly matches token span → Apply override
* **Partial overlap** (snap mode): Override partially overlaps token → Apply with warning
* **No overlap**: Override doesn't touch token → Skip

**Advantages:**

* ✅ Handles duplicate words correctly
* ✅ No ambiguity in complex text
* ✅ Predictable behavior for pipeline integration
* ✅ Works with partial word matches

**Example:**

.. code-block:: python

   result = phonemize(
       "the cat the dog",
       overrides=[
           OverrideSpan(0, 3, {"ph": "ðə"}),
           OverrideSpan(8, 11, {"ph": "ði"}),
       ],
       alignment="span"  # default
   )
   # Both overrides applied to correct "the" instances

2. Legacy Word Alignment
~~~~~~~~~~~~~~~~~~~~~~~~~

**Deprecated.** Uses word-text matching (first occurrence).

**Matching Logic:**

* Finds first token with matching text
* Cannot distinguish between duplicate words
* Provided only for backward compatibility

**Limitations:**

* ❌ Cannot handle duplicate words with different overrides
* ❌ Order-dependent behavior
* ❌ Fragile with whitespace/punctuation variations

**Example:**

.. code-block:: python

   result = phonemize(
       "the cat the dog",
       overrides=[
           OverrideSpan(0, 3, {"ph": "ðə"}),
           OverrideSpan(8, 11, {"ph": "ði"}),  # Will NOT work correctly!
       ],
       alignment="legacy"
   )
   # Only first "the" gets overridden (both overrides apply to same word)

Overlap Handling
----------------

When an override partially overlaps with a token, the system can handle it in two ways via the ``overlap`` parameter in ``phonemize()``:

Snap Mode (Default)
~~~~~~~~~~~~~~~~~~~~

Apply the override and emit a warning:

.. code-block:: python

   result = phonemize(
       "category",
       overrides=[OverrideSpan(0, 3, {"ph": "kæt"})],  # "cat" is only part of "category"
       overlap="snap"
   )
   # Override applied to entire "category" token
   # Warning: "Override span (0, 3) partially overlaps token boundaries; snapping to tokens..."

Strict Mode
~~~~~~~~~~~

Skip the override and emit a warning on partial overlap:

.. code-block:: python

   result = phonemize(
       "category",
       overrides=[OverrideSpan(0, 3, {"ph": "kæt"})],
       overlap="strict"
   )
   # Override skipped
   # Warning: "Override span (0, 3) partially overlaps token boundaries; skipping (strict mode)"

Language Switching
------------------

Override spans can specify language changes for specific text regions:

.. code-block:: python

   # Mix English and French in same sentence
   text = "Hello Bonjour world"
   overrides = [
       OverrideSpan(6, 13, {"lang": "fr"})  # "Bonjour" in French
   ]

   result = phonemize(text, language="en-us", overrides=overrides)
   # "Hello" → English G2P
   # "Bonjour" → French G2P
   # "world" → English G2P

**Language Codes:**

* Use standard language codes: ``en-us``, ``fr``, ``de``, ``es``, etc.
* See ``get_g2p()`` for supported languages

Phoneme Overrides
-----------------

Direct phoneme replacement bypasses G2P processing:

.. code-block:: python

   text = "read the book"
   overrides = [
       OverrideSpan(0, 4, {"ph": "ɹˈEd"}),  # "read" as past tense
   ]

   result = phonemize(text, overrides=overrides)
   # Uses provided phonemes for "read" instead of G2P lookup

**Phoneme Override Priority:** If both ``ph`` and ``lang`` are specified, ``ph`` takes precedence:

.. code-block:: python

   OverrideSpan(0, 5, {"ph": "test", "lang": "fr"})
   # "ph" is used, "lang" is ignored for this span

Custom Attributes
-----------------

Override spans can carry custom attributes for downstream processing:

.. code-block:: python

   overrides = [
       OverrideSpan(0, 5, {
           "ph": "həlˈO",
           "speaker": "male",
           "emphasis": "strong"
       })
   ]

   result = phonemize(text, overrides=overrides)
   # Custom attributes stored in token.meta
   for token in result.tokens:
       print(token.meta)  # {"ph": "həlˈO", "speaker": "male", "emphasis": "strong", ...}

Best Practices
--------------

1. Use Span Alignment (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Always use span-based alignment unless you have a specific reason to use legacy mode:

.. code-block:: python

   # ✅ Good
   result = phonemize(text, overrides=overrides)

   # ❌ Avoid (unless backward compatibility required)
   result = phonemize(text, overrides=overrides, alignment="legacy")

2. Compute Offsets from Clean Text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Always compute offsets from the text **after** markup removal:

.. code-block:: python

   # Original markup text
   markup_text = "[Hello]{ph='test'} world"

   # Remove markup to get clean text
   clean_text = "Hello world"

   # Compute offsets from clean text
   override = OverrideSpan(0, 5, {"ph": "həlˈO"})  # Refers to "Hello" in clean_text

3. Use tokenize() for Debugging
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inspect tokenization to understand offset positions:

.. code-block:: python

   from kokorog2p import tokenize

   text = "the cat the dog"
   tokens = tokenize(text, language="en-us")

   for tok in tokens:
       print(f"{tok.text!r} → [{tok.char_start}:{tok.char_end}]")
   # 'the' → [0:3]
   # ' ' → [3:4]
   # 'cat' → [4:7]
   # ...

4. Check Warnings
~~~~~~~~~~~~~~~~~

Always inspect ``result.warnings`` to catch alignment issues:

.. code-block:: python

   result = phonemize(text, overrides=overrides)

   if result.warnings:
       print("Alignment warnings:")
       for warning in result.warnings:
           print(f"  - {warning}")

5. Test with Duplicates
~~~~~~~~~~~~~~~~~~~~~~~

Always test your override logic with duplicate words:

.. code-block:: python

   # ✅ Good test case
   text = "the cat saw the dog"
   overrides = [
       OverrideSpan(0, 3, {"ph": "ðə"}),    # First "the"
       OverrideSpan(12, 15, {"ph": "ði"}),  # Second "the"
   ]
   result = phonemize(text, overrides=overrides)
   assert len(result.warnings) == 0

Common Pitfalls
---------------

❌ Using Word Offsets Instead of Character Offsets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # WRONG: These are word positions, not character offsets
   override = OverrideSpan(0, 1, {"ph": "test"})  # Trying to select first word

   # RIGHT: Use character positions
   text = "hello world"
   override = OverrideSpan(0, 5, {"ph": "test"})  # "hello" is chars 0-5

❌ Ignoring Clean Text vs Original Text
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # Original with markers: "@Hello@ world"
   # Clean: "Hello world"

   # WRONG: Offsets based on original text with markers
   override = OverrideSpan(0, 7, {"ph": "test"})  # Includes marker chars

   # RIGHT: Offsets based on clean text
   override = OverrideSpan(0, 5, {"ph": "test"})  # Just "Hello"

❌ Forgetting Exclusive End
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   text = "hello"
   #       01234

   # WRONG: Inclusive end
   override = OverrideSpan(0, 4, {"ph": "test"})  # Only covers "hell"

   # RIGHT: Exclusive end
   override = OverrideSpan(0, 5, {"ph": "test"})  # Covers "hello"

❌ Assuming Legacy Alignment Works with Duplicates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # WRONG: Legacy alignment cannot handle this correctly
   text = "the cat the dog"
   overrides = [
       OverrideSpan(0, 3, {"ph": "ðə"}),
       OverrideSpan(8, 11, {"ph": "ði"}),
   ]
   result = phonemize(text, overrides=overrides, alignment="legacy")
   # Both overrides apply to first "the" only!

   # RIGHT: Use span alignment (default)
   result = phonemize(text, overrides=overrides)
   # Correctly applies to each "the" instance

See Also
--------

* :doc:`api/core` - Main API functions
* :doc:`markers` - Convenient marker-based syntax for creating override spans
* :doc:`quickstart` - Getting started with kokorog2p
