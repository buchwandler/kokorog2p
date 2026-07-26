# English API

English G2P provides high-quality phoneme conversion for US and British English.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.en.EnglishG2P
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__

   .. automethod:: __call__

   .. automethod:: phonemize

   .. automethod:: lookup
```

## Lexicon

```{eval-rst}
.. autoclass:: kokorog2p.en.EnglishLexicon
   :members:
   :undoc-members:
   :show-inheritance:

   .. automethod:: __init__

   .. automethod:: lookup

   .. automethod:: is_known

   .. automethod:: __len__
```

## Number Conversion

### Converter Class

```{eval-rst}
.. autoclass:: kokorog2p.en.numbers.NumberConverter
   :members:
   :undoc-members:

   .. automethod:: __init__

   .. automethod:: convert
```

### Helper Functions

```{eval-rst}
.. autofunction:: kokorog2p.en.numbers.is_digit
```

```{eval-rst}
.. autofunction:: kokorog2p.en.numbers.is_currency_amount
```

### Constants

```{eval-rst}
.. autodata:: kokorog2p.en.numbers.ORDINALS
   :annotation:
```

```{eval-rst}
.. autodata:: kokorog2p.en.numbers.CURRENCIES
   :annotation:
```

## Examples

### Basic Usage

```python
from kokorog2p.en import EnglishG2P

# US English
g2p = EnglishG2P(language="en-us")
tokens = g2p("Hello world!")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")

# British English
g2p_gb = EnglishG2P(language="en-gb")
tokens = g2p_gb("Hello world!")
```

### spaCy Model Selection

English G2P uses spaCy for POS tagging when `use_spacy=True`. You can choose the spaCy
English model with `spacy_model`:

```python
from kokorog2p.en import EnglishG2P

# Default model (recommended balance)
g2p_md = EnglishG2P(use_spacy=True, spacy_model="en_core_web_md")

# Smaller model
g2p_sm = EnglishG2P(use_spacy=True, spacy_model="en_core_web_sm")

# Larger model
g2p_lg = EnglishG2P(use_spacy=True, spacy_model="en_core_web_lg")
```

### Dictionary Lookup

```python
from kokorog2p.en import EnglishLexicon

lexicon = EnglishLexicon(language="en-us")

# Simple lookup
phonemes = lexicon.lookup("hello")
print(phonemes)  # həlˈO

# POS-aware lookup
read_present = lexicon.lookup("read", tag="VB")
read_past = lexicon.lookup("read", tag="VBD")
```

### Number Expansion

```python
from kokorog2p.en import EnglishG2P

# Numbers are automatically expanded during G2P processing
g2p = EnglishG2P(language="en-us")
tokens = g2p("I have $42.50 and 3 cats.")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
# → I -> aɪ
# → have -> hæv
# → forty-two dollars and fifty cents -> ...
# → and -> ænd
# → three -> θɹi
# → cats -> kæts
```

### Punctuation Normalization

English G2P automatically normalizes punctuation variants:

```python
from kokorog2p.en import EnglishG2P

g2p = EnglishG2P(language="en-us")

# Apostrophe variants (all normalize to ')
g2p("don't")    # Right single quote (')
g2p("don't")    # Apostrophe (')
g2p("don`t")    # Grave accent (`)
g2p("don´t")    # Acute accent (´)

# Ellipsis variants (all normalize to …)
g2p("Wait...")       # Three dots
g2p("Wait. . .")     # Spaced dots
g2p("Wait…")         # Ellipsis character

# Dash variants (all normalize to — when spaced)
g2p("Wait - now")    # Hyphen with spaces
g2p("Wait -- now")   # Double hyphen
g2p("Wait – now")    # En dash
g2p("Wait — now")    # Em dash
g2p("Wait ― now")    # Horizontal bar
g2p("Wait ‒ now")    # Figure dash
g2p("Wait − now")    # Minus sign

# Compound words keep hyphens (then removed in output)
g2p("well-known")         # Hyphen joins words
g2p("state-of-the-art")   # Multiple hyphens
```

**Normalized Characters:**

- Apostrophes: `'` `'` `'` \`\` \`\` `´` `ʹ` `′` `＇` → `'`

- Ellipsis: `...` `. . .` `..` `....` → `…`

- Dashes (when spaced): `-` `--` `–` `―` `‒` `−` → `—`
