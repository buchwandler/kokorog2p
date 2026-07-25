#!/usr/bin/env python3
"""Rebuild the French gold lexicon using espeak."""

from __future__ import annotations

from pathlib import Path

from kokorog2p.fr.fallback import FrenchFallback
from scripts.rebuild_lexicon_base import rebuild_lexicon_file

ROOT = Path(__file__).resolve().parents[1]
LEXICON_PATH = ROOT / "kokorog2p" / "fr" / "data" / "fr_gold.json"


def main() -> int:
    fallback = FrenchFallback()

    def phonemize(word: str) -> str | None:
        phonemes, _rating = fallback(word)
        return phonemes

    return rebuild_lexicon_file(LEXICON_PATH, LEXICON_PATH, phonemize)


if __name__ == "__main__":
    raise SystemExit(main())
