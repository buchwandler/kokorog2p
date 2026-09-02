#!/usr/bin/env python3
"""Demonstrate explicit language routing for mixed-language prepared text."""

from kokorog2p import OverrideSpan, phonemize_prepared


def main() -> None:
    text = "Hallo world"
    overrides = [OverrideSpan(6, 11, {"lang": "en-us"})]
    result = phonemize_prepared(text, language="de", overrides=overrides)

    print(f"Input: {text}")
    print(f"Phonemes: {result.phonemes}")
    for token in result.tokens:
        print(f"{token.text} ({token.lang}) -> {token.meta.get('phonemes', '')}")


if __name__ == "__main__":
    main()
