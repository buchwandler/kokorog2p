#!/usr/bin/env python3
"""Rebuild the English (US) gold lexicon using espeak."""

from __future__ import annotations

from pathlib import Path

from kokorog2p.en import EnglishG2P
from scripts.rebuild_lexicon_base import rebuild_lexicon_file

ROOT = Path(__file__).resolve().parents[1]
LEXICON_PATH = ROOT / "lexicons" / "sources" / "en" / "us_gold.json"


def main() -> int:
    g2p = EnglishG2P(
        language="en-us",
        use_espeak_fallback=True,
        use_spacy=False,
        load_gold=False,
        load_silver=False,
    )

    def phonemize(word: str) -> str | None:
        return g2p.lookup(word)

    return rebuild_lexicon_file(LEXICON_PATH, LEXICON_PATH, phonemize)


if __name__ == "__main__":
    raise SystemExit(main())
