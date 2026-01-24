====================================
Abbreviation Customization Guide
====================================

Overview
========

The ``kokorog2p`` library provides a flexible abbreviation expansion system that allows you to customize which abbreviations are expanded and how. This is particularly useful when:

- You want to disable specific abbreviations
- You need to add custom abbreviations for domain-specific terms
- You want to change how an abbreviation expands (e.g., always expand "Dr." to "Drive" instead of "Doctor")
- You need context-aware expansions (e.g., "St." → "Street" vs "Saint")

Quick Start
===========

.. code-block:: python

   from kokorog2p import get_g2p

   # Get a G2P instance
   g2p = get_g2p("en-us")

   # Remove an abbreviation
   g2p.remove_abbreviation("Dr.")

   # Add a custom abbreviation
   g2p.add_abbreviation("Dr.", "Drive")

   # Test it
   print(g2p.phonemize("I live on Main Dr."))
   # → 'I live on Main Drive' (phonemized)

API Reference
=============

add_abbreviation()
------------------

.. py:method:: add_abbreviation(abbreviation, expansion, description="", case_sensitive=False)

   Add or update an abbreviation.

   :param str abbreviation: The abbreviation string (e.g., "Dr.", "Tech.")
   :param expansion: Either a simple string expansion or a dict for context-aware expansion
   :type expansion: str or dict
   :param str description: Description of the abbreviation (optional)
   :param bool case_sensitive: Whether matching should be case-sensitive (optional)

   **Examples:**

   .. code-block:: python

      # Simple expansion
      g2p.add_abbreviation("Tech.", "Technology")

      # Context-aware expansion
      g2p.add_abbreviation(
          "Dr.",
          {
              "default": "Drive",
              "title": "Doctor"
          },
          "Doctor or Drive (context-dependent)"
      )

   **Available contexts:**

   - ``default``: Default expansion when context is unknown
   - ``title``: Title/honorific context (e.g., "Dr. Smith")
   - ``place``: Place name context (e.g., "123 Main Dr.")
   - ``time``: Time-related context (e.g., "3 P.M.")
   - ``academic``: Academic degree context (e.g., "Ph.D.")
   - ``religious``: Religious context (e.g., "St. Peter")

   .. note::

      The "St." abbreviation uses an advanced multi-signal detection algorithm:

      - **Priority 1:** Saint/city name recognition (23 names: peter, paul, john, mary, patrick, francis, joseph, michael, george, luke, mark, matthew, thomas, james, anthony, andrew, louis, petersburg, augustine, helena, cloud, albans, andrews)
      - **Priority 2:** House number pattern within 30 characters (e.g., "123 Main")
      - **Priority 3:** Defaults to "Saint" for unknown names

   **Examples:**

   .. code-block:: python

      # Street context (house number pattern)
      g2p.phonemize("123 Main St.")  # → "123 Main Street"

      # Saint context (name recognized)
      g2p.phonemize("St. Patrick's Day")  # → "Saint Patrick's Day"

      # City context (name recognized)
      g2p.phonemize("Visit St. Louis")  # → "Visit Saint Louis"

      # Distant number ignored
      g2p.phonemize("Born in 1850, St. Peter was influential")
      # → "Born in 1850, Saint Peter was influential"

remove_abbreviation()
---------------------

.. py:method:: remove_abbreviation(abbreviation, case_sensitive=False)

   Remove an abbreviation.

   :param str abbreviation: The abbreviation to remove
   :param bool case_sensitive: Whether to match case-sensitively (optional)
   :return: True if the abbreviation was found and removed, False otherwise
   :rtype: bool

   **Example:**

   .. code-block:: python

      g2p.remove_abbreviation("Dr.")  # Returns True
      g2p.remove_abbreviation("Xyz.")  # Returns False (doesn't exist)

has_abbreviation()
------------------

.. py:method:: has_abbreviation(abbreviation, case_sensitive=False)

   Check if an abbreviation exists.

   :param str abbreviation: The abbreviation to check
   :param bool case_sensitive: Whether to match case-sensitively (optional)
   :return: True if the abbreviation exists, False otherwise
   :rtype: bool

   **Example:**

   .. code-block:: python

      if g2p.has_abbreviation("Dr."):
          print("Dr. abbreviation exists")

list_abbreviations()
--------------------

.. py:method:: list_abbreviations()

   Get a list of all registered abbreviations.

   :return: List of abbreviation strings
   :rtype: list[str]

   **Example:**

   .. code-block:: python

      abbrevs = g2p.list_abbreviations()
      print(f"Total: {len(abbrevs)} abbreviations")
      print(abbrevs[:10])  # Show first 10

Common Use Cases
================

1. Disable an Abbreviation
---------------------------

If you don't want "Dr." to be expanded at all:

.. code-block:: python

   g2p = get_g2p("en-us")
   g2p.remove_abbreviation("Dr.")

   # Now "Dr." will be treated as unknown text
   text = "Dr. Smith"
   # "Dr." won't be expanded to "Doctor"

2. Replace an Abbreviation
---------------------------

Replace "Dr." so it always expands to "Drive":

.. code-block:: python

   g2p = get_g2p("en-us")

   # Remove the original
   g2p.remove_abbreviation("Dr.")

   # Add new expansion
   g2p.add_abbreviation("Dr.", "Drive")

   # Test
   print(g2p.phonemize("I live on Main Dr."))
   # "Dr." → "Drive"

3. Add Domain-Specific Abbreviations
-------------------------------------

Add abbreviations for your specific domain:

.. code-block:: python

   g2p = get_g2p("en-us")

   # Add technical abbreviations
   g2p.add_abbreviation("API", "Application Programming Interface")
   g2p.add_abbreviation("ML", "Machine Learning")
   g2p.add_abbreviation("GPU", "Graphics Processing Unit")

   # Use them
   text = "The API uses ML on the GPU."
   print(g2p.phonemize(text))

4. Context-Aware Abbreviations
-------------------------------

Create abbreviations that expand differently based on context:

.. code-block:: python

   g2p = get_g2p("en-us")

   # "Av." can mean "Avenue" or "Average"
   g2p.add_abbreviation(
       "Av.",
       {
           "default": "Average",
           "place": "Avenue"
       }
   )

   # In address context
   print(g2p.phonemize("123 Park Av."))
   # → "123 Park Avenue"

   # In other context
   print(g2p.phonemize("The av. is 50."))
   # → "The average is 50."

5. Batch Customization
----------------------

Customize multiple abbreviations at once:

.. code-block:: python

   g2p = get_g2p("en-us")

   # Remove unwanted abbreviations
   for abbr in ["Dr.", "Mr.", "Mrs.", "Ms."]:
       g2p.remove_abbreviation(abbr)

   # Add custom ones
   custom_abbrevs = {
       "Tech.": "Technology",
       "Corp.": "Corporation",
       "Dept.": "Department"
   }

   for abbr, expansion in custom_abbrevs.items():
       g2p.add_abbreviation(abbr, expansion)

Persistence
===========

Changes to abbreviations **persist** across ``get_g2p()`` calls because they modify the singleton abbreviation expander:

.. code-block:: python

   # First instance
   g2p1 = get_g2p("en-us")
   g2p1.add_abbreviation("Custom.", "Customized")

   # Second instance (same configuration)
   g2p2 = get_g2p("en-us")
   print(g2p2.has_abbreviation("Custom."))  # True

To reset, use ``reset_abbreviations()``:

.. code-block:: python

   from kokorog2p import reset_abbreviations

   reset_abbreviations()  # Reset abbreviation expanders

.. note::

   ``clear_cache()`` only clears cached G2P instances; it does not reset
   abbreviation expanders. ``reset_abbreviations()`` resets expanders and
   clears cached G2P instances.

Advanced: Working with the Expander Directly
=============================================

You can also work directly with the abbreviation expander:

.. code-block:: python

   from kokorog2p.en.abbreviations import get_expander

   expander = get_expander()

   # Get abbreviation details
   entry = expander.get_abbreviation("Dr.")
   print(entry.abbreviation)     # "Dr."
   print(entry.expansion)         # "Doctor" or "Drive"
   print(entry.context_expansions)  # Context-specific expansions
   print(entry.description)       # Description

Notes
=====

1. **Case Sensitivity**: By default, abbreviations are case-insensitive. Use ``case_sensitive=True`` if you need exact matching.

2. **Singleton Behavior**: The abbreviation expander is a singleton, so changes affect all G2P instances using the same language.

3. **Context Detection**: Context-aware expansions require ``enable_context_detection=True`` (default) when creating the G2P instance.

4. **Order Matters**: When removing and adding the same abbreviation, make sure to remove first, then add.

Example Script
==============

See ``examples/abbreviation_customization.py`` for a complete working example demonstrating all features.

Troubleshooting
===============

**Q: My custom abbreviation isn't being expanded.**

A: Check:

- Did you enable abbreviation expansion? (``expand_abbreviations=True`` is default)
- Is the abbreviation properly formatted with punctuation?
- Use ``has_abbreviation()`` to verify it was added

**Q: Changes don't persist after restarting.**

A: Abbreviation customizations are in-memory only. If you need persistent customizations, add them at startup or create a configuration system.

**Q: Context-aware expansion isn't working.**

A: Make sure ``enable_context_detection=True`` when creating the G2P instance (it's the default).

See Also
========

- `English Abbreviations Source <https://github.com/holgern/kokorog2p/blob/main/kokorog2p/en/abbreviations.py>`_ - Default abbreviations
- `Abbreviation Pipeline <https://github.com/holgern/kokorog2p/blob/main/kokorog2p/pipeline/abbreviations.py>`_ - Base framework
- `Examples <https://github.com/holgern/kokorog2p/blob/main/examples/abbreviation_customization.py>`_ - Working examples
