#!/usr/bin/env python3
"""Rebuild the English (US) gold lexicon using espeak."""

from __future__ import annotations

from pathlib import Path

from kokorog2p.en.fallback import EspeakFallback
from scripts.rebuild_lexicon_base import rebuild_lexicon_file

ROOT = Path(__file__).resolve().parents[1]
LEXICON_PATH = ROOT / "kokorog2p" / "en" / "data" / "us_gold.json"


def main() -> int:
    fallback = EspeakFallback(british=False)

    def phonemize(word: str) -> str | None:
        phonemes, _rating = fallback(word)
        return phonemes

    return rebuild_lexicon_file(LEXICON_PATH, LEXICON_PATH, phonemize)


if __name__ == "__main__":
    raise SystemExit(main())
