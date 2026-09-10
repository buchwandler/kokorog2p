#!/usr/bin/env python3
"""Show conservative automatic German-English loanword routing."""

from kokorog2p import LanguageRoutingConfig, phonemize_to_result

TEXT = "Die Manpowerdiskussion wird gecancelt, du kannst das File downloaden."


def main() -> None:
    result = phonemize_to_result(
        TEXT,
        lang="de",
        language_routing=LanguageRoutingConfig(
            mode="auto", languages=("de-de", "en-us")
        ),
        g2p_options={"use_spacy": False, "use_espeak_fallback": True},
        return_ids=False,
    )
    for route in result.language_routes:
        print(route.text)
        for fragment in route.fragments:
            print(f"  {fragment.text} -> {fragment.language}")
    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  {warning}")


if __name__ == "__main__":
    main()
