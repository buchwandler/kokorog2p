# Korean API

Korean G2P uses the vendored 5Hyeons `g2pkc` compatibility rules and the Kokoro 82M v1.0
model alphabet by default. The default Korean voice metadata is `jf_alpha`, using the
Japanese voice requested for Korean synthesis.

## Main Class

```{eval-rst}
.. autoclass:: kokorog2p.ko.KoreanG2P
   :members:
   :undoc-members:
   :show-inheritance:
```

## Examples

```python
from kokorog2p.ko import KoreanG2P

g2p = KoreanG2P(
    language="ko-kr",
    morphology="auto",
    voice="jf_alpha",
    output="model",
)
tokens = g2p("안녕하세요!")

for token in tokens:
    print(f"{token.text} -> {token.phonemes}")
```

Use `output="ipa"` to retain the linguistic IPA-like form and positional coda markers,
or `output="jamo"` to inspect the g2pkc intermediate representation. The `morphology`
setting accepts `auto`, `required`, and `off`. The compatible morphology extra is
`kokorog2p[ko-mecab]`, which installs `python-mecab-ko`.

Pure Hangul input does not load CMUdict. Latin input uses NLTK CMUdict and requires the
resource to be installed explicitly.

## Implementation

The Korean backend is based on the 5Hyeons StyleTTS2 `g2pkc` fork of Kyubyong's g2pK.
See `kokorog2p/ko/README.md` for source revision, checksums, local adaptations, and
licensing provenance.
