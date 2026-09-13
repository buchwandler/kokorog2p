#!/usr/bin/env python3
"""Demonstrate G2P factory cache reuse for prepared-text batches.

This is a cache identity example, not a timing benchmark. It uses the base
rule-based German frontend without external dictionaries or providers.
"""

from kokorog2p import cache_info, clear_cache, get_g2p


def main() -> None:
    clear_cache(deep=True)

    first = get_g2p(
        "de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    second = get_g2p(
        "de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
    )
    distinct = get_g2p(
        "de",
        lexicons=(),
        use_spacy=False,
        use_espeak_fallback=False,
        phoneme_quotes="ascii",
    )

    assert first is second
    assert first is not distinct
    print(f"same configuration reuses instance: {first is second}")
    print(f"changed configuration creates instance: {first is not distinct}")
    print(f"cache: {cache_info()}")

    for text in ("Hallo Welt", "Guten Tag", "Bis morgen"):
        print(f"{text} -> {first.phonemize(text)}")


if __name__ == "__main__":
    main()
