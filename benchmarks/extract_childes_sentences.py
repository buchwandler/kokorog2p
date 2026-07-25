#!/usr/bin/env python3
"""Extract high-quality sentences from CHILDES dataset to enhance synthetic benchmarks.

This script:
1. Reads the large CHILDES IPA dataset
2. Filters for high-quality adult speech
3. Converts espeak IPA to Kokoro phonemes
4. Validates against kokorog2p output
5. Identifies sentences that fill phoneme coverage gaps
6. Exports to synthetic benchmark format

Usage:
    python benchmarks/extract_childes_sentences.py --language en-gb --count 50
    python benchmarks/extract_childes_sentences.py --language en-us --count 100 \
        --output additions.json
    python benchmarks/extract_childes_sentences.py --language en-gb \
        --fill-gaps --phonemes "Q,ɒ,ː,a"
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd


def load_childes_data(language: str, max_rows: int | None = None) -> pd.DataFrame:
    """Load CHILDES dataset for a language.

    Args:
        language: Language code (e.g., "en-us", "en-gb")
        max_rows: Maximum rows to read (None = all)

    Returns:
        DataFrame with CHILDES data
    """
    lang_map = {
        "en-us": "en-US",
        "en-gb": "en-GB",
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


def filter_quality_sentences(
    df: pd.DataFrame,
    min_tokens: int = 3,
    max_tokens: int = 10,
    adult_only: bool = True,
    exclude_roles: list[str] | None = None,
) -> pd.DataFrame:
    """Filter for high-quality sentences.

    Args:
        df: Input DataFrame
        min_tokens: Minimum number of tokens
        max_tokens: Maximum number of tokens
        adult_only: Only include adult speech
        exclude_roles: Speaker roles to exclude

    Returns:
        Filtered DataFrame
    """
    filtered = df.copy()

    # Filter by adult speech
    if adult_only:
        filtered = filtered[not filtered["is_child"]]

    # Filter by sentence length
    filtered = filtered[
        (filtered["num_tokens"] >= min_tokens) & (filtered["num_tokens"] <= max_tokens)
    ]

    # Exclude specific speaker roles
    if exclude_roles:
        filtered = filtered[~filtered["speaker_role"].isin(exclude_roles)]

    # Remove sentences with missing IPA
    filtered = filtered[filtered["ipa_espeak"].notna()]

    # Remove duplicates
    filtered = filtered.drop_duplicates(subset=["sentence"])

    return filtered


def convert_espeak_to_kokoro(ipa_espeak: str, language: str) -> str:
    """Convert espeak IPA to Kokoro phonemes.

    Args:
        ipa_espeak: Espeak IPA string (pipe-separated words)
        language: Language code

    Returns:
        Kokoro phoneme string (space-separated)
    """
    from kokorog2p.phonemes import FROM_ESPEAK

    # espeak format: "word1 | word2 | word3"
    # Replace pipes with spaces and clean up
    ipa = ipa_espeak.replace(" | ", " ").strip()

    # Apply espeak to kokoro conversions
    for old, new in FROM_ESPEAK:
        ipa = ipa.replace(old, new)

    # Handle syllabic ə + l -> ᵊl (only after consonants)
    # This is a simplification; full logic is in phonemes.py
    import re

    # Consonants that can precede syllabic l
    consonants = "bdfhklmnpstvzɡŋɹʃʒðθʤʧ"
    for cons in consonants:
        ipa = re.sub(f"{cons}əl", f"{cons}ᵊl", ipa)

    # Language-specific adjustments for GB
    if language == "en-gb":
        # GB uses Q (əʊ) instead of O (oʊ)
        ipa = ipa.replace("əʊ", "Q")
        # Ensure length marks are preserved
        # (already in espeak output, just validate)

    return ipa


def validate_with_g2p(
    sentence: str, expected_phonemes: str, language: str
) -> tuple[bool, str]:
    """Validate sentence against kokorog2p output.

    Args:
        sentence: Text to phonemize
        expected_phonemes: Expected Kokoro phonemes
        language: Language code

    Returns:
        Tuple of (matches, actual_phonemes)
    """
    from kokorog2p.en import EnglishG2P

    # Create G2P with gold+silver (reference config)
    g2p = EnglishG2P(
        language=language,
        use_espeak_fallback=False,
        use_spacy=False,
        load_gold=True,
        load_silver=True,
    )

    # Phonemize
    tokens = g2p(sentence)
    actual = " ".join(t.phonemes for t in tokens if t.phonemes)

    # Normalize whitespace
    expected_norm = " ".join(expected_phonemes.split())
    actual_norm = " ".join(actual.split())

    return (expected_norm == actual_norm, actual)


def find_phoneme_gaps(
    current_sentences: list[dict], target_phonemes: frozenset[str]
) -> set[str]:
    """Find phonemes missing from current sentences.

    Args:
        current_sentences: List of sentence dictionaries
        target_phonemes: Complete phoneme vocabulary

    Returns:
        Set of missing phonemes
    """
    covered = set()
    for sent in current_sentences:
        phonemes = sent.get("phonemes", "")
        covered.update(c for c in phonemes if c not in (" ", "\t", "\n"))

    return target_phonemes - covered


def calculate_phoneme_distribution(sentences: list[dict]) -> Counter:
    """Calculate phoneme frequency distribution.

    Args:
        sentences: List of sentence dictionaries

    Returns:
        Counter of phoneme frequencies
    """
    counter = Counter()
    for sent in sentences:
        phonemes = sent.get("phonemes", "")
        counter.update(
            c
            for c in phonemes
            if c
            not in (
                " ",
                "\t",
                "\n",
                ".",
                "!",
                "?",
                ",",
                ";",
                ":",
                "-",
                "—",
                "…",
                '"',
                "(",
                ")",
                """, """,
                "❓",
            )
        )

    return counter


def extract_sentences(
    df: pd.DataFrame,
    language: str,
    count: int,
    target_phonemes: set[str] | None = None,
    existing_sentences: list[dict] | None = None,
    strategy: str = "diverse",
) -> list[dict[str, Any]]:
    """Extract sentences from CHILDES data.

    Args:
        df: Filtered CHILDES DataFrame
        language: Language code
        count: Number of sentences to extract
        target_phonemes: Specific phonemes to target (for gap-filling)
        existing_sentences: Existing sentences to avoid duplicates
        strategy: Selection strategy ("diverse", "gaps", "random")

    Returns:
        List of sentence dictionaries
    """
    from kokorog2p.phonemes import GB_VOCAB, US_VOCAB

    vocab = GB_VOCAB if language == "en-gb" else US_VOCAB

    results = []
    seen_text = set()

    # Track existing sentences
    if existing_sentences:
        seen_text.update(s["text"] for s in existing_sentences)

    # Calculate current phoneme distribution
    current_dist = Counter()
    if existing_sentences:
        current_dist = calculate_phoneme_distribution(existing_sentences)

    print(f"\nExtracting {count} sentences using '{strategy}' strategy...")

    # Iterate through dataset
    for _idx, row in df.iterrows():
        if len(results) >= count:
            break

        sentence = row["sentence"].strip()

        # Skip duplicates
        if sentence in seen_text:
            continue

        # Skip very short/long
        if len(sentence) < 5 or len(sentence) > 100:
            continue

        # Skip sentences with special characters that indicate errors
        if any(c in sentence for c in ["@", "#", "$", "%", "^", "&", "*", "+"]):
            continue

        # Convert espeak IPA to Kokoro
        try:
            kokoro_phonemes = convert_espeak_to_kokoro(row["ipa_espeak"], language)
        except Exception as e:
            print(f"Warning: Failed to convert IPA for '{sentence}': {e}")
            continue

        # Validate phonemes are in vocabulary
        invalid_phonemes = set()
        for char in kokoro_phonemes:
            if char not in vocab and char not in (
                " ",
                "\t",
                "\n",
                ".",
                "!",
                "?",
                ",",
                ";",
                ":",
                "-",
                "—",
                "…",
                '"',
                "(",
                ")",
                """, """,
                "❓",
            ):
                invalid_phonemes.add(char)

        if invalid_phonemes:
            # Try validating with actual G2P (slower but more accurate)
            matches, actual_phonemes = validate_with_g2p(
                sentence, kokoro_phonemes, language
            )
            if matches:
                kokoro_phonemes = actual_phonemes
            else:
                # Skip if still has invalid phonemes
                continue

        # Strategy-specific selection
        if strategy == "gaps" and target_phonemes:
            # Check if sentence contains target phonemes
            sentence_phonemes = {c for c in kokoro_phonemes if c in vocab}
            if not sentence_phonemes & target_phonemes:
                continue  # Doesn't contain any target phonemes

        elif strategy == "diverse":
            # Prefer sentences with underrepresented phonemes
            sentence_phonemes = {c for c in kokoro_phonemes if c in vocab}
            # Calculate score: sum of inverse frequencies
            score = sum(1.0 / (current_dist[p] + 1) for p in sentence_phonemes)

            # Simple threshold: skip if score is too low (all phonemes common)
            if score < 2.0 and len(results) > count // 2:
                continue

        # Add to results
        word_count = len(sentence.split())

        results.append(
            {
                "id": len(results) + 1,  # Will be renumbered later
                "text": sentence,
                "phonemes": kokoro_phonemes,
                "category": "childes_extracted",
                "difficulty": "basic"
                if word_count <= 5
                else ("intermediate" if word_count <= 8 else "advanced"),
                "word_count": word_count,
                "contains_oov": False,  # Assume dictionary coverage
                "notes": f"Extracted from CHILDES "
                f"(speaker: {row.get('speaker_role', 'unknown')})",
                "source": "childes",
            }
        )

        seen_text.add(sentence)

        # Update distribution for diverse strategy
        if strategy == "diverse":
            current_dist.update(c for c in kokoro_phonemes if c in vocab)

        if len(results) % 10 == 0:
            print(f"  Extracted {len(results)}/{count}...")

    print(f"✓ Extracted {len(results)} sentences")
    return results


def export_to_json(
    sentences: list[dict[str, Any]], output_path: Path, language: str
) -> None:
    """Export sentences to synthetic benchmark JSON format.

    Args:
        sentences: List of sentence dictionaries
        output_path: Output file path
        language: Language code
    """
    data = {
        "metadata": {
            "version": "1.0.0",
            "language": language,
            "created_date": "2026-01-03",
            "description": f"CHILDES-extracted sentences for {language.upper()} - "
            f"Natural child-directed speech",
            "phoneme_set": "kokoro",
            "total_sentences": len(sentences),
            "source": "CHILDES corpus (ipa-childes-split dataset)",
            "extraction_method": (
                "Filtered adult speech, 3-10 tokens, validated against kokorog2p"
            ),
        },
        "sentences": sentences,
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Exported to: {output_path}")


def merge_with_existing(
    existing_path: Path,
    new_sentences: list[dict[str, Any]],
    output_path: Path | None = None,
) -> None:
    """Merge new sentences with existing synthetic benchmark.

    Args:
        existing_path: Path to existing synthetic JSON
        new_sentences: New sentences to add
        output_path: Output path (default: overwrite existing)
    """
    if output_path is None:
        output_path = existing_path

    # Load existing data
    with open(existing_path) as f:
        data = json.load(f)

    existing_count = len(data["sentences"])

    # Renumber new sentences
    for i, sent in enumerate(new_sentences, start=existing_count + 1):
        sent["id"] = i

    # Append new sentences
    data["sentences"].extend(new_sentences)
    data["metadata"]["total_sentences"] = len(data["sentences"])

    # Update category counts if present
    if "categories" in data["metadata"]:
        category_counts = Counter(s["category"] for s in data["sentences"])
        data["metadata"]["categories"] = dict(category_counts)

    # Save
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Merged {len(new_sentences)} new sentences with {existing_count} existing")
    print(f"✓ Total sentences: {len(data['sentences'])}")
    print(f"✓ Output: {output_path}")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract high-quality sentences from CHILDES dataset"
    )
    parser.add_argument(
        "--language",
        "-l",
        required=True,
        choices=["en-us", "en-gb"],
        help="Language to extract",
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=50,
        help="Number of sentences to extract (default: 50)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output JSON file (default: childes_<lang>.json)",
    )
    parser.add_argument(
        "--merge",
        "-m",
        type=Path,
        help="Merge with existing synthetic benchmark file",
    )
    parser.add_argument(
        "--strategy",
        "-s",
        choices=["diverse", "gaps", "random"],
        default="diverse",
        help="Selection strategy (default: diverse)",
    )
    parser.add_argument(
        "--fill-gaps",
        action="store_true",
        help="Target phonemes missing from existing benchmark",
    )
    parser.add_argument(
        "--phonemes",
        type=str,
        help="Comma-separated list of phonemes to target (e.g., 'Q,ɒ,ː,a')",
    )
    parser.add_argument(
        "--min-tokens",
        type=int,
        default=3,
        help="Minimum number of tokens (default: 3)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=10,
        help="Maximum number of tokens (default: 10)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Maximum rows to read from CHILDES (for testing)",
    )

    args = parser.parse_args()

    # Set output path
    if args.output is None:
        args.output = Path(f"childes_{args.language.replace('-', '_')}.json")

    # Load existing benchmark if merging or filling gaps
    existing_sentences = None
    target_phonemes = None

    if args.merge:
        print(f"Loading existing benchmark: {args.merge}")
        with open(args.merge) as f:
            existing_data = json.load(f)
            existing_sentences = existing_data["sentences"]

        if args.fill_gaps:
            from kokorog2p.phonemes import GB_VOCAB, US_VOCAB

            vocab = GB_VOCAB if args.language == "en-gb" else US_VOCAB
            missing = find_phoneme_gaps(existing_sentences, vocab)
            if missing:
                print(f"\nMissing phonemes: {' '.join(sorted(missing))}")
                target_phonemes = missing
                args.strategy = "gaps"
            else:
                print("\n✓ Existing benchmark has 100% phoneme coverage!")

    # Parse target phonemes if provided
    if args.phonemes:
        target_phonemes = set(args.phonemes.split(","))
        args.strategy = "gaps"
        print(f"Targeting phonemes: {' '.join(sorted(target_phonemes))}")

    # Load CHILDES data
    df = load_childes_data(args.language, max_rows=args.max_rows)

    # Filter for quality
    print("\nFiltering for quality sentences...")
    df_filtered = filter_quality_sentences(
        df,
        min_tokens=args.min_tokens,
        max_tokens=args.max_tokens,
        adult_only=True,
    )
    print(f"✓ Filtered to {len(df_filtered):,} quality sentences")

    # Extract sentences
    extracted = extract_sentences(
        df_filtered,
        language=args.language,
        count=args.count,
        target_phonemes=target_phonemes,
        existing_sentences=existing_sentences,
        strategy=args.strategy,
    )

    if not extracted:
        print("\n✗ No sentences extracted!")
        return 1

    # Show sample
    print("\n=== Sample Extracted Sentences ===")
    for sent in extracted[:5]:
        print(f"{sent['text']}")
        print(f"  → {sent['phonemes']}")
        print()

    # Export or merge
    if args.merge:
        merge_with_existing(args.merge, extracted, args.output if args.output else None)
    else:
        export_to_json(extracted, args.output, args.language)

    # Show phoneme coverage
    from kokorog2p.phonemes import GB_VOCAB, US_VOCAB

    vocab = GB_VOCAB if args.language == "en-gb" else US_VOCAB

    all_sentences = existing_sentences + extracted if existing_sentences else extracted
    covered = set()
    for sent in all_sentences:
        covered.update(c for c in sent["phonemes"] if c in vocab)

    coverage = len(covered) / len(vocab) * 100
    print(f"\n✓ Phoneme coverage: {len(covered)}/{len(vocab)} ({coverage:.1f}%)")

    if coverage < 100:
        missing = vocab - covered
        print(f"  Missing: {' '.join(sorted(missing))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
