#!/usr/bin/env python3
"""Demonstrate prepared text and explicit pronunciation overrides."""

from kokorog2p import OverrideSpan, phonemize_prepared


def main() -> None:
    prepared = "The temperature is thirty-seven degrees Celsius."
    result = phonemize_prepared(prepared, language="en-us", use_spacy=False)
    print(f"Prepared input: {prepared}")
    print(f"Phonemes: {result.phonemes}")

    prepared = "Doctor Smith lives on Elm Drive."
    result = phonemize_prepared(prepared, language="en-us", use_spacy=False)
    print(f"Externally prepared text: {prepared}")
    print(f"Phonemes: {result.phonemes}")

    prepared = "Hallo world"
    overrides = [OverrideSpan(6, 11, {"lang": "en-us"})]
    result = phonemize_prepared(
        prepared,
        language="de",
        overrides=overrides,
        use_spacy=False,
    )
    print(f"Explicit mixed-language span: {result.phonemes}")


if __name__ == "__main__":
    main()
