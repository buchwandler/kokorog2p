#!/usr/bin/env python3
"""Regenerate phonemes in synthetic data using actual G2P output.

This ensures phonemes match what the G2P system actually produces,
including punctuation marks and context-dependent pronunciations.
"""

import json
import sys
from pathlib import Path

from kokorog2p.de import GermanG2P
from kokorog2p.en import EnglishG2P
from kokorog2p.fr import FrenchG2P
from kokorog2p.ja import JapaneseG2P
from kokorog2p.ko import KoreanG2P
from kokorog2p.zh import ChineseG2P


def regenerate_phonemes(input_file: Path, output_file: Path | None = None) -> None:
    """Regenerate phonemes using G2P output.

    Args:
        input_file: Path to input synthetic JSON file
        output_file: Path to output file (default: overwrite input)
    """
    if output_file is None:
        output_file = input_file

    # Load existing data
    with open(input_file) as f:
        data = json.load(f)

    # Auto-detect language from metadata
    language = data.get("metadata", {}).get("language", "en-us")
    print(f"Detected language: {language}")

    # Create appropriate G2P based on language
    if language in ("en-us", "en-gb"):
        g2p = EnglishG2P(
            language=language,
            use_espeak_fallback=True,  # Enable fallback for OOV words
            use_spacy=False,
            load_gold=True,
            load_silver=True,
        )
    elif language in ("de", "de-de"):
        g2p = GermanG2P(
            use_espeak_fallback=False,
            load_gold=True,
            load_silver=False,
        )
    elif language in ("ja", "ja-jp"):
        g2p = JapaneseG2P(
            use_espeak_fallback=False,
            load_gold=True,
            load_silver=True,
        )
    elif language in ("fr", "fr-fr"):
        g2p = FrenchG2P(
            use_espeak_fallback=False,
            use_spacy=False,
            load_gold=True,
            load_silver=True,
        )
    elif language in ("ko", "ko-kr"):
        g2p = KoreanG2P(
            use_espeak_fallback=False,
            use_dict=True,
        )
    elif language in ("zh", "zh-cn", "cmn"):
        g2p = ChineseG2P(
            use_espeak_fallback=False,
            version="1.1",  # Use ZHFrontend with Zhuyin notation
        )
    else:
        raise ValueError(f"Unsupported language: {language}")

    updated_count = 0
    unchanged_count = 0

    print(f"Regenerating phonemes for {len(data['sentences'])} sentences...")
    print()

    for sentence in data["sentences"]:
        sent_id = sentence["id"]
        text = sentence["text"]
        old_phonemes = sentence["phonemes"]

        # Phonemize
        tokens = g2p(text)

        # Extract ALL phonemes (including punctuation)
        # For Chinese/Japanese/Korean, phonemes are character-based (no spaces)
        # For other languages, join with spaces
        if language in ("zh", "zh-cn", "cmn", "ja", "ja-jp", "ko", "ko-kr"):
            new_phonemes = "".join(t.phonemes for t in tokens if t.phonemes)
        else:
            new_phonemes = " ".join(t.phonemes for t in tokens if t.phonemes)

        # Update if different
        if old_phonemes != new_phonemes:
            print(f"Sentence {sent_id}:")
            print(f"  Old: {old_phonemes}")
            print(f"  New: {new_phonemes}")
            print()
            sentence["phonemes"] = new_phonemes
            updated_count += 1
        else:
            unchanged_count += 1

    # Save updated data
    with open(output_file, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("✓ Complete!")
    print(f"  Updated: {updated_count} sentences")
    print(f"  Unchanged: {unchanged_count} sentences")
    print(f"  Output: {output_file}")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Regenerate phonemes in synthetic data"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input synthetic JSON file",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file (default: overwrite input)",
    )

    args = parser.parse_args()

    if not args.input.exists():
        print(f"Error: File not found: {args.input}")
        return 1

    regenerate_phonemes(args.input, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
