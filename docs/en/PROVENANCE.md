# English Kokoro frontend provenance

## Reference

The English realization contract is based on `hexgrad/misaki`, specifically
`misaki/en.py` at commit `fba1236595f2d2bf21d414ba6e57d25256afada3`, package version
`0.9.4`, frontend `misaki.en.G2P`.

The pinned implementation is the compatibility oracle for model-facing English phoneme
behavior. The reference package is used only by isolated benchmark and review tooling.
KokoroG2P does not import Misaki at runtime.

## Ported semantic areas

- POS parent selectors and tagged heteronym selection.
- Context-sensitive function words and right-to-left future-vowel/future-to state.
- Capitalization-derived stress.
- Proper-noun and letter-name spelling.
- Productive `-s`, `-ed`, and `-ing` morphology.
- Unicode-aware lexical subtokenization and grouped resolution.
- Compound stress balancing.
- Legacy English frontend finalization.

The realization order is:

```text
selected source value
    -> source codec
    -> lexical and morphological realization
    -> subtoken/compound stress resolution
    -> profile finalization
    -> Kokoro inventory validation
```

`en-us:gold` stores `kokoro-v1` values. The logical gold asset represents the legacy
gold and silver data after the G2Lex transform, including case aliases and gold
precedence. Those dataset semantics belong to the G2Lex data layer and are not
reconstructed in KokoroG2P.

`en-us:lexhint` stores IPA values and uses the same realization path after the English
IPA-to-Kokoro codec. The source encoding is therefore data metadata, not a second
English frontend.

## Intentional differences

KokoroG2P intentionally differs from the reference architecture in these areas:

- No runtime Misaki dependency.
- External G2Lex resources with lazy shared leases.
- Lexphon-owned fallback providers.
- KokoroG2P's public `GToken` and debug/provenance model.
- Prepared-text APIs keep written-to-spoken semantic expansion outside the core.
- Consolidated gold/silver data is selected by the G2Lex transform.

These differences are allowed only when they do not change the model-facing English
realization contract. Any retained phoneme difference must be recorded in a regression
test and explained here.

## Compatibility profile

The initial internal profile is `hexgrad-misaki-v1`. It enables compound stress
resolution and uses the legacy finalization rewrites:

```text
ɾ -> T
ʔ -> t
```

The profile is deliberately separate from KokoroG2P's public target-model `version`
field. A target model version and a frontend compatibility version are independent
concepts.

## Contract corpus

`benchmarks/reference/data/en_us_misaki_contract_v1.json` is the maintained review
corpus. It covers tagged entries, function words, capitalization, morphology, compounds,
punctuation context boundaries, proper-noun spelling, compound stress, and generated
flap/glottal finalization. Cases are compared to the pinned reference with stage-aware
diagnostics when the reference environment is available.
