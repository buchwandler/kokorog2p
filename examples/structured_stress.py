#!/usr/bin/env python3
"""Demonstrate structured stress overrides on prepared text.

The example uses rule-based German phonemization with no external resources.
"""

from kokorog2p import OverrideSpan, phonemize_prepared

TEXT = "Hallo Welt"


def run(overrides=()):
    return phonemize_prepared(
        TEXT,
        language="de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        overrides=overrides,
        return_ids=False,
    )


def main() -> None:
    base = run()
    primary = run([OverrideSpan(0, 5, {"stress": "+2"})])
    unstressed = run([OverrideSpan(0, 5, {"stress": "-2"})])

    print(f"base:       {base.phonemes}")
    print(f"primary:    {primary.phonemes}")
    print(f"unstressed: {unstressed.phonemes}")


if __name__ == "__main__":
    main()
