#!/usr/bin/env python3
"""Helper script to generate phonemes for synthetic benchmark sentences.

This script helps create ground truth phonemes for benchmark sentences by:
1. Using the gold dictionary for known words
2. Cross-validating with espeak and goruut for OOV words
3. Allowing manual override for conflicts

Usage:
    python generate_phonemes.py "The quick brown fox jumps."
"""

import json
from pathlib import Path


def get_gold_phonemes(word: str, language: str = "en-us") -> str | None:
    """Look up word in gold dictionary."""
    data_dir = Path(__file__).parent.parent / "kokorog2p" / "en" / "data"
    gold_path = data_dir / "us_gold.json"

    with open(gold_path) as f:
        gold_dict = json.load(f)

    result = gold_dict.get(word.lower())
    if isinstance(result, dict):
        # Heteronym - return DEFAULT
        return result.get("DEFAULT")
    return result


def get_espeak_phonemes(word: str) -> str | None:
    """Get phonemes using espeak backend."""
    try:
        from kokorog2p.en.fallback import EspeakFallback

        espeak = EspeakFallback(british=False)
        phonemes, _rating = espeak(word)
        return phonemes
    except Exception:
        return None


def get_goruut_phonemes(word: str) -> str | None:
    """Get phonemes using goruut backend."""
    try:
        from kokorog2p.backends.goruut import GoruutBackend

        if GoruutBackend.is_available():
            goruut = GoruutBackend(language="en-us")
            return goruut.word_phonemes(word)
    except ImportError:
        pass
    return None


def generate_sentence_phonemes(
    text: str, verbose: bool = True
) -> dict[str, dict[str, str | None]]:
    """Generate phonemes for each word in a sentence.

    Args:
        text: The sentence text
        verbose: Whether to print detailed info

    Returns:
        Dictionary mapping words to their phonemes with source info
    """
    from kokorog2p.en import EnglishG2P

    # Tokenize the sentence
    g2p = EnglishG2P(language="en-us", use_espeak_fallback=False, use_spacy=False)
    tokens = g2p(text)

    results = {}

    for token in tokens:
        if not token.is_word:
            continue

        word = token.text.lower()

        # Try gold dictionary first
        gold = get_gold_phonemes(word)
        espeak = get_espeak_phonemes(word)
        goruut = get_goruut_phonemes(word)

        # Choose source (prefer gold, then cross-validate)
        if gold:
            source = "gold"
            phonemes = gold
        elif goruut and espeak and goruut == espeak:
            source = "espeak+goruut (match)"
            phonemes = espeak
        elif goruut:
            source = "goruut"
            phonemes = goruut
        elif espeak:
            source = "espeak"
            phonemes = espeak
        else:
            source = "UNKNOWN"
            phonemes = ""

        result_data = {
            "phonemes": phonemes,
            "source": source,
            "gold": gold,
            "espeak": espeak,
            "goruut": goruut,
        }
        results[word] = result_data

        if verbose:
            print(f"{word:20} -> {phonemes if phonemes else 'NONE':20} [{source}]")
            if gold and espeak and gold != espeak:
                print(f"  ⚠ MISMATCH: gold={gold}, espeak={espeak}")
            if goruut and espeak and goruut != espeak:
                print(f"  ⚠ MISMATCH: goruut={goruut}, espeak={espeak}")

    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate phonemes for benchmark sentences"
    )
    parser.add_argument("text", help="Sentence text to phonemize")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")

    args = parser.parse_args()

    results = generate_sentence_phonemes(args.text, verbose=not args.quiet)

    # Print final phoneme string
    phonemes = " ".join(
        r.get("phonemes") or "" for r in results.values() if r.get("phonemes")
    )
    print(f"\nFinal phonemes: {phonemes}")

    # Check for conflicts
    conflicts = [
        word
        for word, data in results.items()
        if data.get("gold")
        and data.get("espeak")
        and data.get("gold") != data.get("espeak")
    ]
    if conflicts:
        print(f"\n⚠ {len(conflicts)} conflicts detected: {conflicts}")


if __name__ == "__main__":
    main()
