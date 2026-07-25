#!/usr/bin/env python3
"""Demo: multilang preprocessing with span-based API."""

from kokorog2p import phonemize
from kokorog2p.multilang import preprocess_multilang


def main() -> None:
    text = "Schöne World! Bonjour world!"
    overrides = preprocess_multilang(
        text,
        default_language="en-us",
        allowed_languages=["en-us", "de", "fr"],
    )

    print("Input:")
    print(f"  {text}")
    print("\nDetected language spans:")
    for span in overrides:
        segment = text[span.char_start : span.char_end]
        print(f"  '{segment}' → {span.attrs}")

    result = phonemize(text, language="en-us", overrides=overrides)

    print("\nPhonemes:")
    print(f"  {result.phonemes}")
    print("\nTokens with languages:")
    for token in result.tokens:
        phonemes = token.meta.get("phonemes", "")
        print(f"  {token.text} ({token.lang}) → {phonemes}")


if __name__ == "__main__":
    main()
