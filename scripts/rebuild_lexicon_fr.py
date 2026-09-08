#!/usr/bin/env python3
"""Rebuild the French gold lexicon using espeak."""

from __future__ import annotations

from pathlib import Path

from kokorog2p.fr import FrenchG2P
from scripts.rebuild_lexicon_base import rebuild_lexicon_file

ROOT = Path(__file__).resolve().parents[1]
LEXICON_PATH = ROOT / "lexicons" / "sources" / "fr" / "fr_gold.json"


def main() -> int:
    g2p = FrenchG2P(
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
