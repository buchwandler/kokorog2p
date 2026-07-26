# Japanese API

Japanese G2P uses pyopenjtalk for text analysis and mora-based phoneme generation.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.ja.JapaneseG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Examples

```python
from kokorog2p.ja import JapaneseG2P

g2p = JapaneseG2P(language="ja")
tokens = g2p("こんにちは世界")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
```

## Features

- pyopenjtalk for full Japanese text analysis
- Mora-based phoneme generation
- Automatic pitch accent assignment
- Japanese numeral handling
