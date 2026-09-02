#!/usr/bin/env python3
"""Demonstrate the prepared-text and span-based KokoroG2P API."""

from kokorog2p import OverrideSpan, phonemize_prepared


def main() -> None:
    text = "Hello world!"
    result = phonemize_prepared(text, language="en-us")
    print(f"{text} -> {result.phonemes}")

    text = "Hello world!"
    overrides = [OverrideSpan(0, 5, {"ph": "hɛˈloʊ"})]
    result = phonemize_prepared(text, language="en-us", overrides=overrides)
    print(f"phoneme override -> {result.phonemes}")

    text = "the cat the dog"
    overrides = [
        OverrideSpan(0, 3, {"ph": "ðə"}),
        OverrideSpan(8, 11, {"ph": "ði"}),
    ]
    result = phonemize_prepared(text, language="en-us", overrides=overrides)
    print(f"duplicate-word overrides -> {result.phonemes}")

    text = "Hello Bonjour Welt"
    overrides = [
        OverrideSpan(6, 13, {"lang": "fr"}),
        OverrideSpan(14, 18, {"lang": "de"}),
    ]
    result = phonemize_prepared(text, language="en-us", overrides=overrides)
    print(f"explicit language spans -> {result.phonemes}")

    text = "Say Bonjour nicely"
    overrides = [OverrideSpan(4, 11, {"ph": "bɔ̃ʒuʁ", "lang": "fr"})]
    result = phonemize_prepared(text, language="en-us", overrides=overrides)
    print(f"combined override -> {result.phonemes}")

    text = "Hello world"
    overrides = [OverrideSpan(2, 8, {"ph": "test"})]
    result = phonemize_prepared(text, language="en-us", overrides=overrides)
    print(f"snapped override warnings -> {result.warnings}")


if __name__ == "__main__":
    main()
