#!/usr/bin/env python3
"""Demo: SpeechMarkdown annotations."""

from kokorog2p import get_g2p


def main() -> None:
    text = (
        'You say, (pecan)[ipa:"pɪˈkɑːn"]. '
        "I say, (pecan)[/ˈpi.kæn/]. "
        'In Paris, they pronounce it (Paris)[lang:"fr-FR"].'
    )

    g2p = get_g2p("en-us", markdown_syntax="speechmarkdown")
    print("Input:")
    print(f"  {text}")
    print("\nPhonemes:")
    print(f"  {g2p.phonemize(text)}")


if __name__ == "__main__":
    main()
