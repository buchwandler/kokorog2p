#!/usr/bin/env python3
"""Demonstrate explicit named lexicon selection and lexical evidence.

Prerequisites:

    python -m pip install "kokorog2p[de]"
    lexphon data install de-de:crane
    lexphon data verify de-de:crane

The data commands are provisioning steps for the shell, not downloads performed
by this example.
"""

from kokorog2p import available_lexicons, get_g2p, lexicon_info

LANGUAGE = "de"
LEXICON = "crane"


def main() -> None:
    names = available_lexicons(LANGUAGE)
    print(f"Available {LANGUAGE} lexicons: {names}")
    print(f"Selected metadata: {dict(lexicon_info(LANGUAGE, LEXICON))}")

    g2p = get_g2p(
        LANGUAGE,
        lexicons=LEXICON,
        use_spacy=False,
        use_espeak_fallback=False,
        use_goruut_fallback=False,
    )

    for word in ("Haus", "Die"):
        phonemes = g2p.word_to_phonemes(word)
        evidence = g2p.lexicon_evidence(word)
        print(f"{word} -> {phonemes}")
        if evidence is None:
            print("  lexical evidence: none")
        else:
            print(f"  lexicon id: {evidence.lexicon_id}")
            print(f"  lexicon name: {evidence.lexicon_name}")
            print(f"  rating: {evidence.rating}")

    # Ordered stacks are explicit too: the first matching layer wins.
    # Ensure both assets are provisioned before enabling this variant:
    # lexphon data install de-de:crane de-de:gold
    # lexphon data verify de-de:crane de-de:gold
    # stacked = get_g2p("de", lexicons=("crane", "gold"), use_spacy=False)


if __name__ == "__main__":
    main()
