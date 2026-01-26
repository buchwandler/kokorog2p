Marker-Delimited Helper Guide
==============================

The marker-delimited helper provides a simple, human-friendly way to mark text spans for pronunciation overrides without complex syntax. It's designed as a lightweight alternative for users who don't need full markup capabilities.

Overview
--------

The marker system uses simple delimiters (like ``@``) to mark text spans, then lets you assign attributes to those spans using Python dictionaries. This two-step process separates the marking from the attribute assignment.

Basic Usage
-----------

.. code-block:: python

   from kokorog2p.markers import parse_delimited, apply_marker_overrides
   from kokorog2p import phonemize

   # Step 1: Parse marked text
   text = "Ich mag @New York@. @Hi@ Klaus."
   clean_text, ranges, warnings = parse_delimited(text, marker="@")
   # clean_text: "Ich mag New York. Hi Klaus."
   # ranges: [(8, 16), (18, 20)]  # Positions of "New York" and "Hi"

   # Step 2: Assign attributes to marked spans
   assignments = {
       1: {"ph": "nuː jɔːk"},      # First marker: phoneme override
       2: {"lang": "en-us"},        # Second marker: language switch
   }
   overrides = apply_marker_overrides(clean_text, ranges, assignments)

   # Step 3: Phonemize with overrides
   result = phonemize(clean_text, language="de", overrides=overrides)
   print(result.phonemes)

API Reference
-------------

parse_delimited
~~~~~~~~~~~~~~~

Extracts marked spans from text and returns clean text with character offset ranges.

.. code-block:: python

   def parse_delimited(text, marker="@", escape="\\"):
       """
       Parameters:
           text (str): Input text with marker-delimited spans
           marker (str): Delimiter character (default: "@")
           escape (str): Escape character for literal markers (default: "\\")

       Returns:
           tuple: (clean_text, marked_ranges, warnings)
               - clean_text: Text with markers removed
               - marked_ranges: List of (char_start, char_end) tuples
               - warnings: List of warning messages (unmatched/nested markers)
       """

**Examples:**

.. code-block:: python

   # Basic marking
   parse_delimited("I like @coffee@.")
   # ('I like coffee.', [(7, 13)], [])

   # Multiple marks
   parse_delimited("I like @coffee@ and @tea@.")
   # ('I like coffee and tea.', [(7, 13), (18, 21)], [])

   # Escaped marker (literal @)
   parse_delimited("Email: user\\@example.com")
   # ('Email: user@example.com', [], [])

   # Unmatched marker (warning)
   parse_delimited("Unmatched @marker")
   # ('Unmatched @marker', [], ['Unmatched opening marker at position 10'])

apply_marker_overrides
~~~~~~~~~~~~~~~~~~~~~~

Converts marked ranges and attribute assignments to ``OverrideSpan`` objects.

.. code-block:: python

   def apply_marker_overrides(clean_text, marked_ranges, assignments):
       """
       Parameters:
           clean_text (str): Clean text from parse_delimited
           marked_ranges (list): List of (char_start, char_end) tuples
           assignments (list | dict): Attributes for each marker:
               - List: Applied in order (must match range count)
               - Dict: 1-based index mapping (e.g., {1: {...}, 2: {...}})

       Returns:
           list: List of OverrideSpan objects for phonemize
       """

**Examples:**

.. code-block:: python

   ranges = [(7, 13), (18, 21)]

   # List-based (in order)
   assignments = [{"ph": "ˈkɔfi"}, {"lang": "en-us"}]
   overrides = apply_marker_overrides("", ranges, assignments)

   # Dict-based (1-indexed)
   assignments = {
       1: {"ph": "ˈkɔfi"},
       2: {"lang": "en-us"}
   }
   overrides = apply_marker_overrides("", ranges, assignments)

   # Selective assignment (only second marker)
   assignments = {2: {"lang": "en-us"}}
   overrides = apply_marker_overrides("", ranges, assignments)

Parsing Rules
-------------

Marker Pairing
~~~~~~~~~~~~~~

Markers must come in pairs (opening and closing):

.. code-block:: python

   text = "@word@"  # Valid
   text = "@word"   # Invalid - unmatched marker (warning)
   text = "word@"   # Literal @ (no opening marker)

Escaping
~~~~~~~~

Use the escape character to include literal markers in text:

.. code-block:: python

   # Default escape character is backslash
   parse_delimited("Email: user\\@example.com", marker="@")
   # Output: "Email: user@example.com" (no ranges)

   # Custom escape character
   parse_delimited("Price: 5|$", marker="$", escape="|")
   # Output: "Price: 5$" (no ranges)

Nested Markers
~~~~~~~~~~~~~~

Nested markers are **not supported** and generate warnings:

.. code-block:: python

   text = "@outer @inner@ outer@"
   clean_text, ranges, warnings = parse_delimited(text)
   # Warning: "Nested markers detected at position 14"
   # Result: Single range covering entire span

**Best Practice:** Avoid nesting markers. Use non-overlapping spans instead.

Unmatched Markers
~~~~~~~~~~~~~~~~~

Unmatched opening markers generate warnings and are kept as literal text:

.. code-block:: python

   text = "Start @unmatched end"
   clean_text, ranges, warnings = parse_delimited(text)
   # clean_text: "Start @unmatched end"
   # ranges: []
   # warnings: ['Unmatched opening marker at position 6']

Assignment Strategies
---------------------

List-Based (In Order)
~~~~~~~~~~~~~~~~~~~~~

Use a list when you want to assign attributes in the order markers appear:

.. code-block:: python

   text = "I like @coffee@ and @tea@ and @water@."
   clean_text, ranges, warnings = parse_delimited(text)

   # Must provide exactly 3 assignments (one per marker)
   assignments = [
       {"ph": "ˈkɔfi"},
       {"ph": "tiː"},
       {"lang": "en-us"},
   ]
   overrides = apply_marker_overrides(clean_text, ranges, assignments)

**Advantages:**

* Simple and concise for sequential assignments
* No need to count marker positions

**Limitations:**

* Must provide assignment for every marker
* Cannot skip markers easily

Dict-Based (1-Indexed)
~~~~~~~~~~~~~~~~~~~~~~

Use a dict when you want selective or non-sequential assignment:

.. code-block:: python

   text = "I like @coffee@ and @tea@ and @water@."
   clean_text, ranges, warnings = parse_delimited(text)

   # Apply attributes only to markers 1 and 3 (skip marker 2)
   assignments = {
       1: {"ph": "ˈkɔfi"},
       3: {"lang": "en-us"},
   }
   overrides = apply_marker_overrides(clean_text, ranges, assignments)

**Advantages:**

* Selective assignment (can skip markers)
* Explicit marker numbering (clearer intent)
* Easier to modify/reorder

**Limitations:**

* Must use 1-based indexing (not 0-based)
* More verbose for simple sequential cases

Attribute Types
---------------

Phoneme Override (ph)
~~~~~~~~~~~~~~~~~~~~~

Directly specify phonemes for a word:

.. code-block:: python

   text = "I like @pecan@ pie."
   clean_text, ranges, _ = parse_delimited(text)

   assignments = {1: {"ph": "pɪˈkɑːn"}}
   overrides = apply_marker_overrides(clean_text, ranges, assignments)

   result = phonemize(clean_text, overrides=overrides)
   # "pecan" pronounced as /pɪˈkɑːn/

Language Switch (lang)
~~~~~~~~~~~~~~~~~~~~~~

Switch language for specific words:

.. code-block:: python

   text = "I like @Bonjour@ and @Hola@."
   clean_text, ranges, _ = parse_delimited(text)

   assignments = {
       1: {"lang": "fr"},
       2: {"lang": "es"},
   }
   overrides = apply_marker_overrides(clean_text, ranges, assignments)

   result = phonemize(clean_text, language="en-us", overrides=overrides)
   # "Bonjour" uses French G2P, "Hola" uses Spanish G2P

Combined Attributes
~~~~~~~~~~~~~~~~~~~

You can combine multiple attributes:

.. code-block:: python

   assignments = {
       1: {
           "ph": "nuː jɔːk",
           "speaker": "male",
           "emphasis": "strong"
       }
   }

**Note:** ``ph`` and ``lang`` are special attributes handled by kokorog2p. Other attributes are stored in token metadata for downstream processing.

Custom Markers
--------------

You can use any single character as a marker:

.. code-block:: python

   # Using hash marks
   parse_delimited("I like #coffee#.", marker="#")

   # Using asterisks
   parse_delimited("I like *coffee*.", marker="*")

   # Using dollar signs
   parse_delimited("Price: $100$ USD.", marker="$")

**Best Practice:** Choose markers that are unlikely to appear naturally in your text.

Common Patterns
---------------

Handling Duplicate Words
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   text = "@the@ cat @the@ dog"
   clean_text, ranges, _ = parse_delimited(text)

   assignments = {
       1: {"ph": "ðə"},  # First "the" (reduced)
       2: {"ph": "ði"},  # Second "the" (emphasized)
   }
   overrides = apply_marker_overrides(clean_text, ranges, assignments)
   result = phonemize(clean_text, overrides=overrides)

Multi-Word Spans
~~~~~~~~~~~~~~~~

Markers can wrap multiple words:

.. code-block:: python

   text = "I visited @New York City@ last year."
   clean_text, ranges, _ = parse_delimited(text)

   assignments = {1: {"ph": "nuː jɔːk ˈsɪti"}}
   overrides = apply_marker_overrides(clean_text, ranges, assignments)

Mixed Language Text
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   text = "Das ist @Machine Learning@ für @Performance@."
   clean_text, ranges, _ = parse_delimited(text)

   assignments = {
       1: {"lang": "en-us"},  # "Machine Learning"
       2: {"lang": "en-us"},  # "Performance"
   }
   overrides = apply_marker_overrides(clean_text, ranges, assignments)
   result = phonemize(clean_text, language="de", overrides=overrides)

Error Handling
--------------

The marker system provides warnings rather than errors for robustness:

.. code-block:: python

   text = "@unmatched and @nested @marker@ here@"
   clean_text, ranges, warnings = parse_delimited(text)

   for warning in warnings:
       print(f"Warning: {warning}")
   # Warning: Unmatched opening marker at position 0
   # Warning: Nested markers detected at position ...

   # Text is still usable - warnings help debug issues

**When to Check Warnings:**

* During development/testing
* When user input quality is uncertain
* For production validation

Comparison with Direct Span Creation
-------------------------------------

Using Markers (Convenient)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   text = "I like @coffee@."
   clean_text, ranges, _ = parse_delimited(text)
   overrides = apply_marker_overrides(clean_text, ranges, {1: {"ph": "ˈkɔfi"}})
   result = phonemize(clean_text, overrides=overrides)

Direct Spans (More Control)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   text = "I like coffee."
   overrides = [OverrideSpan(7, 13, {"ph": "ˈkɔfi"})]
   result = phonemize(text, overrides=overrides)

**When to Use Markers:**

* User-facing applications where users mark text
* Quick prototyping and experimentation
* Text with many override regions

**When to Use Direct Spans:**

* Programmatic override generation
* Precise offset control needed
* Integration with external text processing pipelines

See Also
--------

* :doc:`spans` - Understanding character offsets and OverrideSpan
* :doc:`api/core` - Complete kokorog2p API documentation
* :doc:`quickstart` - Getting started with kokorog2p
