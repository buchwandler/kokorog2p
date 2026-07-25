#!/usr/bin/env python3
"""Fast extraction of CHILDES sentences - optimized version.

This version:
- Skips slow G2P validation during extraction
- Uses text-based deduplication
- Processes in batches
- Can validate afterwards with separate script

Usage:
    # Extract 140 new sentences for GB
    python benchmarks/extract_childes_fast.py --language en-gb --count 140 \
        --merge benchmarks/data/en_gb_synthetic.json

    # Extract for US
    python benchmarks/extract_childes_fast.py --language en-us --count 105 \
        --merge benchmarks/data/en_us_synthetic.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


def load_childes_data(language: str, max_rows: int | None = None) -> pd.DataFrame:
    """Load CHILDES dataset."""
    lang_map = {
        "en-us": "en-US",
        "en-gb": "en-GB",
        "de": "de-DE",
        "de-de": "de-DE",
        "fr": "fr-FR",
        "fr-fr": "fr-FR",
        "es": "es-ES",
        "es-es": "es-ES",
        "ja": "ja-JP",
        "ja-jp": "ja-JP",
        "ko": "ko-KR",
        "ko-kr": "ko-KR",
    }
    lang_dir = lang_map.get(language)
    if not lang_dir:
        raise ValueError(f"Unsupported language: {language}")

    filepath = Path(__file__).parent / "ipa-childes-split" / lang_dir / "data.csv"
    if not filepath.exists():
        raise FileNotFoundError(f"CHILDES data not found: {filepath}")

    print(f"Loading CHILDES data from {filepath}...")
    df = pd.read_csv(filepath, nrows=max_rows)
    print(f"Loaded {len(df):,} rows")

    return df


def convert_espeak_to_kokoro_fast(ipa_espeak: str, language: str = "en-us") -> str:
    """Fast espeak to Kokoro conversion (without validation).

    Uses simplified conversion rules. May need manual review.
    """
    # espeak format: "word1 | word2 | word3"
    ipa = ipa_espeak.replace(" | ", " ").strip()

    # Language-specific conversions
    if language in ("en-us", "en-gb"):
        # Apply basic conversions from kokorog2p.phonemes
        conversions = [
            # Diphthongs
            ("a͡ɪ", "I"),
            ("a͡ʊ", "W"),
            ("e͡ɪ", "A"),
            ("ɔ͡ɪ", "Y"),
            # Affricates
            ("d͡ʒ", "ʤ"),
            ("t͡ʃ", "ʧ"),
            # Common substitutions
            ("r", "ɹ"),
            ("x", "k"),
            ("ç", "k"),
            ("ɬ", "l"),
            # Rhotacized vowels
            ("ɚɹ", "əɹ"),
            ("ɚ", "əɹ"),
            # Other
            ("e", "A"),
            ("ɐ", "ə"),
        ]
    elif language in ("de", "de-de"):
        # German conversions
        conversions = [
            # Affricates with tie bars
            ("t͡s", "ʦ"),
            ("t͡ʃ", "ʧ"),
            ("d͡ʒ", "ʤ"),
            # Remove combining diacritics
            ("\u032f", ""),  # non-syllabic marker
            ("\u0329", ""),  # syllabic marker
            # Keep German-specific phonemes as is
        ]
    else:
        # Generic conversions for other languages
        conversions = [
            ("t͡s", "ʦ"),
            ("t͡ʃ", "ʧ"),
            ("d͡ʒ", "ʤ"),
            ("\u032f", ""),
            ("\u0329", ""),
        ]

    for old, new in conversions:
        ipa = ipa.replace(old, new)

    return ipa


def extract_fast(
    df: pd.DataFrame,
    language: str,
    count: int,
    existing_texts: set[str],
    min_tokens: int = 3,
    max_tokens: int = 10,
) -> list[dict[str, Any]]:
    """Fast extraction without G2P validation."""

    results = []
    seen_text = existing_texts.copy()

    print(f"\nExtracting {count} sentences...")
    print(f"Already have {len(existing_texts)} existing sentences to avoid")

    # Pre-filter dataframe for speed
    df_filtered = df[
        (~df["is_child"])  # Adult only (use ~ for boolean negation)
        & (df["num_tokens"] >= min_tokens)
        & (df["num_tokens"] <= max_tokens)
        & (df["ipa_espeak"].notna())
    ].copy()

    print(f"Filtered to {len(df_filtered):,} candidate sentences")

    processed = 0
    for _idx, row in df_filtered.iterrows():
        if len(results) >= count:
            break

        processed += 1
        if processed % 10000 == 0:
            print(
                f"  Processed {processed:,} rows, extracted {len(results)}/{count}..."
            )

        sentence = row["sentence"].strip()

        # Skip duplicates
        if sentence.lower() in seen_text:
            continue

        # Skip very short/long
        if len(sentence) < 5 or len(sentence) > 100:
            continue

        # Skip sentences with error markers
        if any(c in sentence for c in ["@", "#", "$", "%", "^", "&", "*", "+"]):
            continue

        # Skip nonsense/babbling (common in child speech data)
        if sentence.count("h") > len(sentence) // 2:  # "hhh", "ahhah"
            continue

        # Convert espeak IPA
        try:
            kokoro_phonemes = convert_espeak_to_kokoro_fast(row["ipa_espeak"], language)
        except Exception:
            continue

        # Basic sanity check - should have some phonemes
        if len(kokoro_phonemes) < 3:
            continue

        # Add to results
        word_count = len(sentence.split())

        results.append(
            {
                "id": len(results) + 1,
                "text": sentence,
                "phonemes": kokoro_phonemes,
                "category": "childes_natural",
                "difficulty": "basic"
                if word_count <= 5
                else ("intermediate" if word_count <= 8 else "advanced"),
                "word_count": word_count,
                "contains_oov": False,
                "notes": f"CHILDES natural speech ({row.get('speaker_role', 'adult')})",
                "source": "childes",
                "childes_id": int(row["id"]) if pd.notna(row.get("id")) else None,
            }
        )

        seen_text.add(sentence.lower())

        if len(results) % 20 == 0:
            print(f"  Extracted {len(results)}/{count}...")

    print(f"✓ Extracted {len(results)} sentences")
    return results


def merge_with_existing(
    existing_path: Path,
    new_sentences: list[dict[str, Any]],
    output_path: Path | None = None,
) -> None:
    """Merge new sentences with existing synthetic benchmark."""

    if output_path is None:
        output_path = existing_path

    # Load existing
    with open(existing_path) as f:
        data = json.load(f)

    existing_count = len(data["sentences"])

    # Renumber all sentences (existing + new)
    all_sentences = data["sentences"] + new_sentences
    for i, sent in enumerate(all_sentences, start=1):
        sent["id"] = i

    data["sentences"] = all_sentences
    data["metadata"]["total_sentences"] = len(all_sentences)

    # Update category counts
    category_counts = Counter(s["category"] for s in all_sentences)
    data["metadata"]["categories"] = dict(category_counts)

    # Save
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(
        f"✓ Merged {len(new_sentences)} new + {existing_count} existing = "
        f"{len(all_sentences)} total"
    )
    print(f"✓ Output: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Fast CHILDES extraction")
    parser.add_argument(
        "--language",
        "-l",
        required=True,
        choices=[
            "en-us",
            "en-gb",
            "de",
            "de-de",
            "fr",
            "fr-fr",
            "es",
            "es-es",
            "ja",
            "ja-jp",
            "ko",
            "ko-kr",
        ],
    )
    parser.add_argument(
        "--count", "-n", type=int, required=True, help="Number of sentences to extract"
    )
    parser.add_argument("--merge", "-m", type=Path, help="Merge with existing file")
    parser.add_argument(
        "--output", "-o", type=Path, help="Output path (default: overwrite merge file)"
    )
    parser.add_argument("--min-tokens", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=10)
    parser.add_argument("--max-rows", type=int, help="Limit CHILDES rows (for testing)")

    args = parser.parse_args()

    # Load existing texts to avoid duplicates
    existing_texts = set()
    if args.merge:
        print(f"Loading existing: {args.merge}")
        with open(args.merge) as f:
            existing_data = json.load(f)
            for sent in existing_data["sentences"]:
                existing_texts.add(sent["text"].lower())

    # Load CHILDES
    df = load_childes_data(args.language, max_rows=args.max_rows)

    # Extract
    extracted = extract_fast(
        df,
        language=args.language,
        count=args.count,
        existing_texts=existing_texts,
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
    )

    if not extracted:
        print("\n✗ No sentences extracted!")
        return 1

    # Show samples
    print("\n=== Sample Extracted Sentences ===")
    for sent in extracted[:10]:
        print(f"  {sent['text']}")

    # Merge or save
    if args.merge:
        merge_with_existing(args.merge, extracted, args.output)
    else:
        output = args.output or Path(f"childes_{args.language.replace('-', '_')}.json")
        data = {
            "metadata": {
                "version": "1.0.0",
                "language": args.language,
                "created_date": "2026-01-03",
                "description": f"CHILDES-extracted natural speech for {args.language}",
                "phoneme_set": "kokoro",
                "total_sentences": len(extracted),
                "source": "CHILDES corpus",
            },
            "sentences": extracted,
        }
        with open(output, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved to: {output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
