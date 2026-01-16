#!/usr/bin/env python3
"""Demo: multilang preprocessing with SSMD annotations."""

from kokorog2p import phonemize_with_ssmd
from kokorog2p.multilang import preprocess_multilang


def main() -> None:
    text = "Schöne World! Bonjour world!"
    annotated = preprocess_multilang(
        text,
        default_language="en-us",
        allowed_languages=["en-us", "de", "fr"],
    )

    print("Input:")
    print(f"  {text}")
    print("\nAnnotated:")
    print(f"  {annotated}")
    print("\nPhonemes:")
    print(f"  {phonemize_with_ssmd(annotated, language='en-us')}")


if __name__ == "__main__":
    main()
