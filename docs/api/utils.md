# Utilities API

This page documents utility modules and helper functions.

## Token Context

```{eval-rst}
.. autoclass:: kokorog2p.en.lexicon.TokenContext
   :members:
   :undoc-members:
```

## Generic provider handling

Generic eSpeak and Goruut fallback ownership is provided by Lexphon 0.2 through the
shared `LexphonBackend` adapter. Native frontends retain target-language IPA
normalization, Kokoro conversion, ratings, and diagnostics. Provider results are not
lexical routing evidence.

Direct `backend="espeak"` and `backend="goruut"` remain documented in the backend API
and are independent compatibility paths.

## Internal Utilities

These are internal utilities used by the library. They may change without notice.

### Lexicon Utilities

Functions for working with lexicons and dictionaries.

### Number Processing

Internal number processing utilities shared across languages.
