# Kazakh G2P

Kazakh (`kk`) is a native eSpeak-NG frontend. Install the existing eSpeak integration:

```bash
pip install "kokorog2p[kk]"
```

The frontend uses the eSpeak-NG `kk` voice and requests raw non-English IPA. It preserves
ordinary Kazakh IPA semantics and applies only small generic tied-phoneme compatibility
transforms before validating output against the stock Kokoro 1.0 vocabulary.

```python
from kokorog2p import get_g2p, phonemize

# All aliases share one cached instance.
g2p = get_g2p("kazakh")
assert g2p is get_g2p("kk")

result = phonemize("Сәлем әлем!", language="kk")
print(result.phonemes)
```

`KazakhG2P` preserves punctuation, whitespace, source offsets, and `espeak` ratings on
successful lexical tokens. `strict=True` reports missing voices, empty output, and symbols
outside the target vocabulary. `strict=False` keeps the established lenient behavior and
leaves failed lexical tokens without phonemes.

The upstream eSpeak-NG Kazakh voice is currently marked `testing`, so pronunciation quality
follows the installed eSpeak-NG release. This package does not copy eSpeak rules, download
models, or install Epitran or Misaki.
