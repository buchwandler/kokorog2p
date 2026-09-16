# Backends API

kokorog2p supports multiple phonemization backends.

## espeak-ng Backend

```{eval-rst}
.. autoclass:: kokorog2p.backends.espeak.EspeakBackend
   :members:
   :undoc-members:
   :show-inheritance:
```

```{eval-rst}
.. autoclass:: kokorog2p.espeak_g2p.EspeakOnlyG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## goruut Backend

```{eval-rst}
.. autoclass:: kokorog2p.goruut_g2p.GoruutOnlyG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Examples

### espeak Backend

```python
from kokorog2p.backends.espeak import EspeakBackend

backend = EspeakBackend(language="en-us")
phonemes = backend.phonemize("hello")
print(phonemes)
```

`EspeakBackend` delegates discovery and native/CLI lifecycle to `espeakng-runtime`.
Default mode prefers native and falls back to CLI; `use_cli=True` forces CLI. Inspect
the selected implementation after first use with `backend.runtime_info`, then call
`backend.close()` when the instance is no longer needed.

The neutral runtime configuration variables are `ESPEAKNG_RUNTIME_EXECUTABLE`,
`ESPEAKNG_RUNTIME_LIBRARY`, and `ESPEAKNG_RUNTIME_DATA`. The legacy
`KOKOROG2P_ESPEAK_EXECUTABLE`, `KOKOROG2P_ESPEAK_LIBRARY`, and `KOKOROG2P_ESPEAK_DATA`
variables remain compatibility aliases. This direct backend is distinct from the Lexphon
eSpeak fallback selected with `use_espeak_fallback=True`.

### Using espeak-only G2P

```python
from kokorog2p.espeak_g2p import EspeakOnlyG2P

# Strict mode (default) - raises errors if espeak fails
g2p = EspeakOnlyG2P(language="es-es", strict=True)
tokens = g2p("Hola mundo")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")

# Lenient mode - returns empty on errors (backward compatible)
g2p_lenient = EspeakOnlyG2P(language="es-es", strict=False)
tokens = g2p_lenient("Hola mundo")
```

### Using goruut Backend

```python
from kokorog2p.goruut_g2p import GoruutOnlyG2P

# Strict mode (default)
g2p = GoruutOnlyG2P(language="en-us", strict=True)
tokens = g2p("Hello world")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")

# Lenient mode
g2p_lenient = GoruutOnlyG2P(language="en-us", strict=False)
tokens = g2p_lenient("Hello world")
```
