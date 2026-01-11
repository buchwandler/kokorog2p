Changelog
=========

All notable changes to kokorog2p will be documented in this file.

Unreleased
----------

Version 0.4.0 (2026-01-11)
--------------------------

Added
~~~~~

* **New ``strict`` parameter** for error handling control in all G2P backends

  - ``strict=True`` (default): Raises detailed ``RuntimeError`` when backends fail
  - ``strict=False`` (lenient mode): Logs errors and returns empty strings (backward compatible)
  - Available in: ``get_g2p()``, ``EspeakG2P``, ``GoruutG2P``, ``EnglishG2P``, and base ``G2P`` class
  - Includes in cache key to ensure correct behavior for different strict modes

* Early backend validation in ``EspeakG2P._validate_backend()`` to catch initialization errors immediately
* Comprehensive logging throughout error handling paths
* 15 new tests in ``tests/test_ci_bug_fix.py`` covering strict/lenient modes and error scenarios
* Detailed error handling documentation in README.md and docs/advanced.rst
* CI/CD best practices guide for proper espeak-ng installation

Changed
~~~~~~~

* **BREAKING CHANGE**: Silent exception handling removed - errors now raise by default

  - Previous behavior: Exceptions were caught and empty strings returned silently
  - New behavior: Exceptions raise ``RuntimeError`` with detailed context (use ``strict=False`` for old behavior)
  - Affected methods: ``phonemize()``, ``__call__()``, ``lookup()`` in all backends

* Improved error messages with actionable debugging information
* Enhanced fallback logging in ``EspeakFallback`` and ``GoruutFallback`` classes
* Updated documentation with comprehensive error handling examples

Fixed
~~~~~

* **Critical bug fix**: Fixed silent failures in CI environments that returned empty strings instead of raising errors

  - Root cause: 8 locations with bare ``except Exception`` blocks that silently returned empty strings
  - Impact: Tests passed in CI even when backends failed completely
  - Solution: Proper error propagation with detailed error messages in strict mode
  - Files fixed: ``espeak_g2p.py`` (4 locations), ``goruut_g2p.py`` (3 locations), ``en/fallback.py`` (2 locations)

* Fixed missing error context in backend initialization failures
* Improved error handling for voice not found scenarios in espeak
* Enhanced subprocess error reporting in espeak backend

Migration Guide
~~~~~~~~~~~~~~~

**For users upgrading from v0.3.x or earlier:**

If your code relied on silent failures (empty strings on errors), you have two options:

1. **Recommended**: Fix the underlying issues causing errors (e.g., install espeak-ng properly)

2. **Quick fix**: Use ``strict=False`` to maintain backward compatibility:

   .. code-block:: python

      # Old behavior (silent failures)
      g2p = get_g2p("en-us", backend="espeak", strict=False)

**For CI/CD environments:**

* Ensure espeak-ng is properly installed before running tests
* Use strict mode (default) to catch configuration issues early
* See docs/advanced.rst for CI best practices

Previous Unreleased Changes
----------------------------

Added
~~~~~

* German G2P module with 738k+ entry dictionary
* Czech G2P module with rule-based phonology
* French G2P module with gold dictionary
* Comprehensive test suite (469 tests including 37 new contraction tests)
* Benchmarking framework for performance testing
* Contraction merging for spaCy tokenizer in English G2P
* Test coverage for single and double contractions (don't, could've, I'd've, etc.)

Changed
~~~~~~~

* Improved English contraction handling with intelligent token merging
* Enhanced number conversion for all languages
* Better error handling for missing dependencies
* Updated documentation with multi-language support examples
* Improved type annotations and mypy configuration

Fixed
~~~~~

* Fixed contraction tokenization in English (don't was incorrectly split as "Do" + "n't")
* Fixed Chinese tone_sandhi import type annotation
* Fixed GToken __post_init__ to handle None values for extension dict
* Fixed stress marker handling in German
* Improved phonological rules for Czech
* Fixed documentation API references for English and French modules

Version 0.1.0 (Initial Release)
-------------------------------

Added
~~~~~

* Core G2P framework
* English G2P (US and GB variants)
* Chinese G2P with jieba and pypinyin
* Japanese G2P with pyopenjtalk
* espeak-ng backend support
* goruut backend support (experimental)
* Number and currency handling
* Phoneme vocabulary encoding/decoding
* Punctuation normalization
* Word mismatch detection
* Comprehensive API documentation
* Test suite with 300+ tests

Features
~~~~~~~~

* Dictionary-based lookup with gold/silver tiers
* POS-aware pronunciation for English
* Automatic stress assignment
* Multi-backend support
* Caching for performance
* Type hints throughout
* Full IPA support
