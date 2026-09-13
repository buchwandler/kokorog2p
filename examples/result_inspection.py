#!/usr/bin/env python3
"""Inspect the complete prepared-phonemization result.

This example uses no dictionary or provider layer, so it needs only the base
KokoroG2P installation and does not download external resources.
"""

from kokorog2p import ids_to_phonemes, phonemize_prepared


def main() -> None:
    result = phonemize_prepared(
        "Hallo Welt!",
        language="de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        return_phonemes=True,
        return_ids=True,
    )

    print(f"clean_text: {result.clean_text!r}")
    print(f"extended_text: {result.extended_text!r}")
    print(f"phonemes: {result.phonemes}")
    print(f"token_ids: {result.token_ids}")
    print(f"decoded IDs: {ids_to_phonemes(result.token_ids)}")

    print("tokens:")
    for token in result.tokens:
        print(
            f"  [{token.char_start}:{token.char_end}] "
            f"{token.text!r} -> {token.meta.get('phonemes', '')!r}"
        )

    if result.warnings:
        print("warnings:")
        for warning in result.warnings:
            print(f"  {warning}")


if __name__ == "__main__":
    main()
