#!/usr/bin/env python3
"""Demonstrate the dynamic Lexphon eSpeak fallback provider.

This intentionally uses ``lexicons=()`` so every word misses the dictionary
layer and the difference between fallback disabled and enabled is observable.

Prerequisites:

    python -m pip install "kokorog2p[espeak]"

A system ``espeak-ng`` or ``espeak`` executable must also be discoverable on
``PATH``. For example, install ``espeak-ng`` with ``apt`` or Homebrew before
running this script. This example never installs or downloads resources.

Important distinction: ``lexicons="espeak"`` selects the static German
``de-de:espeak`` lexicon. It is not the same feature as
``use_espeak_fallback=True``, which enables this dynamic provider after a
lexicon miss.
"""

from kokorog2p import get_g2p

WORD = "fallbackdemo"


def describe(use_espeak_fallback: bool) -> None:
    g2p = get_g2p(
        "en-us",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=use_espeak_fallback,
        use_goruut_fallback=False,
    )
    token = next(token for token in g2p(WORD) if token.is_word)

    print(f"use_espeak_fallback={use_espeak_fallback}")
    print(f"  text: {token.text}")
    print(f"  phonemes: {token.phonemes}")
    print(f"  rating: {token.get('rating')}")
    print(f"  source: {token.get('pronunciation_source')}")
    print(f"  provider: {token.get('pronunciation_provider')}")
    print(f"  requested language: {token.get('pronunciation_requested_language')}")
    print(f"  source IPA: {token.get('pronunciation_source_ipa')}")

    if use_espeak_fallback:
        assert token.phonemes
        assert token.get("pronunciation_source") == "provider"
        assert token.get("pronunciation_provider") == "espeak"


def main() -> None:
    describe(False)
    print()
    describe(True)


if __name__ == "__main__":
    main()
