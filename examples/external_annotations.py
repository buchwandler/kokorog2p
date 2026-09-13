#!/usr/bin/env python3
"""Demonstrate caller-supplied POS/tag annotations without spaCy.

Prerequisites:

    lexphon data install en-us:gold
    lexphon data verify en-us:gold

The data commands are explicit provisioning steps. This script does not install
or download the lexicon, and the annotation itself is supplied by the caller.
"""

from kokorog2p import TokenAnnotation, phonemize_prepared

TEXT = "record"


def phonemize_with(annotation: TokenAnnotation):
    return phonemize_prepared(
        TEXT,
        language="en-us",
        lexicons="gold",
        use_spacy=False,
        use_espeak_fallback=False,
        annotations=[annotation],
        return_ids=False,
    )


def main() -> None:
    noun = phonemize_with(TokenAnnotation(0, 6, TEXT, pos="NOUN", tag="NN"))
    verb = phonemize_with(TokenAnnotation(0, 6, TEXT, pos="VERB", tag="VB"))

    print(f"noun: {noun.phonemes}")
    print(f"verb: {verb.phonemes}")
    print(f"noun annotation: {noun.tokens[0].meta}")
    print(f"verb annotation: {verb.tokens[0].meta}")


if __name__ == "__main__":
    main()
