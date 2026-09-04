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

## Cutlet membership dictionary

The optional Cutlet backend uses the provisioned Lexphon `ja:lexhint` dictionary for
lazy known-word membership checks. KokoroG2P does not package a Japanese word-list
source or generated membership asset. Install the local asset before using Cutlet:

```bash
lexphon data install ja:lexhint
lexphon data verify ja:lexhint
```

The default PyOpenJTalk backend retains its existing pronunciation and pitch path and
does not require the LexHint asset.
