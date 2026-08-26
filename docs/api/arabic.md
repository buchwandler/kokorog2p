# Arabic MSA

KokoroG2P provides a native Arabic frontend for Modern Standard Arabic (MSA).
It is not a dialect frontend and does not identify or convert Arabic dialects.

## Construction

```python
from kokorog2p import get_g2p, phonemize

g2p = get_g2p("ar", diacritizer="none")
result = phonemize(
    "مَرْحَبًا بِكَ؟",
    language="ar",
    g2p=g2p,
    return_phonemes=True,
    return_ids=True,
)
```

The native frontend uses the existing Arabic eSpeak-ng voice and raw IPA. It
then applies a small Nabra cleanup policy and targets `nabra-82m-v0.1`. The
Nabra profile reserves IDs 7 and 8 for `ʕ` and `ħ`; those IDs are intended for
the Nabra model, not stock Kokoro 1.0.

## Diacritization

Already-vocalized text can use `diacritizer="none"` and does not require CAMeL
Tools. Unvocalized text can use `diacritizer="auto"` (the default), which uses
CAMeL when its local package and data are available and otherwise emits a
warning and continues. Use `diacritizer="camel-tools"` with
`strict_diacritizer=True` when missing dependencies or data must fail.

CAMeL and its MSA data are optional. KokoroG2P never downloads or provisions
that data. Install the optional package and provision
`disambig-mle-calima-msa-r13` using CAMeL Tools' documented workflow.

Adapters can be injected when a different local diacritizer is required. Each
adapter must return one output token for every input Arabic lexical token.

## Source behavior and offsets

- Arabic harakat remain attached to their lexical source token.
- ASCII Latin runs are suppressed by default with `latin_policy="drop"`.
- Numeric square-bracket citation spans such as `[12]` are suppressed.
- Real parentheses remain distinct and are not treated as citations.
- Source token offsets always refer to the original input string.
- `،`, `؛`, and `؟` are mapped to `,`, `;`, and `?` after source classification.

Arabic numbers, dates, currencies, and dialect-specific normalization are not
implemented by this frontend. Those belong to the upstream semantic
normalization architecture.

## Generic eSpeak backend

`get_g2p("ar", backend="espeak")` intentionally returns the generic
`EspeakOnlyG2P`. It does not select the Nabra cleanup or vocabulary profile.
