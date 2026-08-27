# Thai G2P

Thai support is a native optional frontend targeting `wayu-kokoro-thai-v1`. Install it
with:

```bash
pip install "kokorog2p[th]"
```

The aliases `th`, `th-th`, `tha`, and `thai` share one cached frontend:

```python
from kokorog2p import phonemize

result = phonemize("สวัสดี", language="th", return_ids=True)
print(result.phonemes)
print(result.token_ids)
```

## Behavior

Thai runs use TLTK with PyThaiNLP segmentation for recovery. Latin runs use the existing
EnglishG2P lazily, so ordinary phrases such as `text to speech` are pronounced as
English rather than spelled as Thai letter names. Whitespace and supported punctuation
remain source-aligned.

The frontend version is `1.0`; its target model is the separate `wayu-kokoro-thai-v1`
vocabulary profile. That profile maps the Thai low-tone symbol `˩` to token ID 7 and is
isolated from stock Kokoro and Nabra profiles. Do not combine this profile with another
incompatible custom profile in one ID stream.

## Normalization

The local Thai normalizer handles Thai digits, cardinal and decimal numbers, ranges,
repetition marks, common currency and operator forms, punctuation folding, conservative
chat elongation, and tested identifier/time forms. Thai combining marks are preserved.
Thai semantic ownership remains local until a released `spokenform` version provides the
required Thai semantics.

## Strictness and diagnostics

`strict=True` raises after a lexical Thai unit remains unrecovered or the engine
produces an invalid model symbol. `strict=False` retains recovered material and places
diagnostic warnings on the frontend and public `PhonemizeResult` where available.
Diagnostics include engine exceptions, empty or truncated output, unrecovered words,
invalid model symbols, unsupported source symbols, and unrecovered Latin fallback runs.

TLTK and PyThaiNLP are optional and are loaded only by the Thai frontend. A missing
installation raises an actionable error recommending `kokorog2p[th]`. The pinned Wayu
behavior baseline and clean-room deviations are documented in {doc}`../th/PROVENANCE`.
