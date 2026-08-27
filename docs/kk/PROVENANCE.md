# Kazakh provenance

- kokorog2p does not copy eSpeak-NG Kazakh spelling rules into Python.
- eSpeak-NG is invoked as the external runtime pronunciation engine with voice `kk`.
- The upstream Kazakh language declaration, spelling rules, and letter/number list were
  inspected to establish supported scope.
- Misaki's generic eSpeak architecture informed the raw-IPA compatibility design, but
  Misaki is not a runtime dependency.
- Epitran was researched as an optional differential benchmark reference only.
- The Kazakh Kokoro fine-tune model card was used as interoperability evidence that a
  Kokoro-derived model already uses eSpeak-NG for `kk`.

The upstream eSpeak-NG Kazakh voice currently reports status `testing`. The benchmark is
therefore diagnostic and avoids treating one eSpeak release's exact IPA output as a
permanent gold standard.
