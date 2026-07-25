#!/usr/bin/env python3
"""Validation script for synthetic benchmark data files.

This script validates that synthetic benchmark files:
1. Match the expected JSON schema
2. Contain valid Kokoro phonemes
3. Have accurate phoneme coverage statistics
4. Are internally consistent

Usage:
    python validate_synthetic_data.py benchmarks/data/en_us_synthetic.json
    python validate_synthetic_data.py --all  # Validate all synthetic files
"""

import json
import sys
from pathlib import Path
from typing import Any


def get_vocab_for_language(language: str) -> frozenset[str]:
    """Get the phoneme vocabulary for a language.

    Args:
        language: Language code (e.g., "en-us", "en-gb", "de", "fr", "ja", "ko", "zh")

    Returns:
        Frozenset of valid phoneme characters
    """
    from kokorog2p.phonemes import (
        ES_VOCAB,
        FR_VOCAB,
        GB_VOCAB,
        IT_VOCAB,
        JA_VOCAB,
        KO_VOCAB,
        PT_BR_VOCAB,
        US_VOCAB,
        ZH_VOCAB,
    )

    if language == "en-us":
        return US_VOCAB
    elif language == "en-gb":
        return GB_VOCAB
    elif language in ("ja", "ja-jp"):
        return JA_VOCAB
    elif language in ("fr", "fr-fr"):
        return FR_VOCAB
    elif language in ("ko", "ko-kr"):
        return KO_VOCAB
    elif language in ("zh", "zh-cn", "cmn"):
        return ZH_VOCAB
    elif language in ("it", "it-it"):
        return IT_VOCAB
    elif language in ("es", "es-es", "es-la"):
        return ES_VOCAB
    elif language in ("pt-br", "pt"):
        return PT_BR_VOCAB
    elif language in ("de", "cs"):
        # For now, return US vocab as baseline
        # TODO: Add proper German/Czech vocab
        return US_VOCAB
    else:
        raise ValueError(f"Unknown language: {language}")


def validate_phonemes(phonemes: str, vocab: frozenset[str]) -> tuple[bool, list[str]]:
    """Validate that all phonemes are in the vocabulary.

    Args:
        phonemes: Phoneme string to validate
        vocab: Set of valid phoneme characters

    Returns:
        Tuple of (is_valid, list of invalid characters)
    """
    # Allowed punctuation marks (treated as phonemes by G2P)
    allowed_punctuation = frozenset('!?.,;:—…"()""❓-')

    # Split by spaces to get word phonemes, then check each character
    invalid_chars = []
    for phoneme_char in phonemes:
        if (
            phoneme_char not in vocab
            and phoneme_char not in allowed_punctuation
            and phoneme_char not in (" ", "\t", "\n")
        ):
            invalid_chars.append(phoneme_char)

    return (len(invalid_chars) == 0, list(set(invalid_chars)))


def validate_metadata(data: dict[str, Any]) -> list[str]:
    """Validate metadata section.

    Args:
        data: Parsed JSON data

    Returns:
        List of error messages
    """
    errors = []

    if "metadata" not in data:
        errors.append("Missing 'metadata' section")
        return errors

    metadata = data["metadata"]
    required_fields = [
        "version",
        "language",
        "created_date",
        "description",
        "phoneme_set",
        "total_sentences",
    ]

    for field in required_fields:
        if field not in metadata:
            errors.append(f"Missing required metadata field: {field}")

    # Validate phoneme_set
    if metadata.get("phoneme_set") != "kokoro":
        errors.append(
            f"Expected phoneme_set='kokoro', got '{metadata.get('phoneme_set')}'"
        )

    # Validate total_sentences matches actual count
    if "sentences" in data:
        actual_count = len(data["sentences"])
        expected_count = metadata.get("total_sentences", 0)
        if actual_count != expected_count:
            errors.append(
                f"Metadata total_sentences ({expected_count}) doesn't match "
                f"actual count ({actual_count})"
            )

    return errors


def validate_sentence(
    sentence: dict[str, Any], vocab: frozenset[str], index: int
) -> list[str]:
    """Validate a single sentence entry.

    Args:
        sentence: Sentence dictionary
        vocab: Valid phoneme vocabulary
        index: Sentence index (for error reporting)

    Returns:
        List of error messages
    """
    errors = []

    required_fields = ["id", "text", "phonemes", "category", "difficulty", "word_count"]
    for field in required_fields:
        if field not in sentence:
            errors.append(f"Sentence {index}: Missing required field '{field}'")

    # Validate ID matches index
    if sentence.get("id") != index + 1:
        errors.append(
            f"Sentence {index}: ID mismatch "
            f"(expected {index + 1}, got {sentence.get('id')})"
        )

    # Validate phonemes
    phonemes = sentence.get("phonemes", "")
    is_valid, invalid = validate_phonemes(phonemes, vocab)
    if not is_valid:
        errors.append(
            f"Sentence {index} (ID {sentence.get('id')}): Invalid phonemes: {invalid}"
        )

    # Validate category
    valid_categories = {
        "phoneme_coverage",
        "stress_patterns",
        "contractions",
        "common_words",
        "diphthongs",
        "oov_words",
        "numbers_punctuation",
        "compounds",
        "minimal_pairs",
        "mixed_difficulty",
        "gb_specific",  # GB-specific phoneme features
        "childes_natural",  # Natural speech from CHILDES corpus
        # Japanese/Korean/Chinese/multilingual categories
        "greetings",
        "questions",
        "numbers",
        "verbs",
        "adjectives",
        "conversation",
        "food",  # Food and drink vocabulary
        # Italian-specific categories
        "palatals",  # Palatal consonants (gn, gli, nh, lh, ch)
        "affricates",  # Affricates (c/ci, g/gi, z, t+i, d+i)
        "gemination",  # Double consonants
        "vowels",  # Vowel sequences
        "complex",  # Complex sentences
        # Chinese-specific categories
        "phoneme_initials",  # Zhuyin initial coverage
        "phoneme_finals",  # Zhuyin final coverage
        "tone_coverage",  # All 5 Mandarin tones
        "complex_phonemes",  # Complex syllables and compounds
        # Spanish-specific categories
        "jota",  # Jota sound (j, g+e/i)
        "theta",  # Theta sound (z, c+e/i) - European Spanish
        "r_sounds",  # R tap vs trill distinction
        # Portuguese-specific categories
        "sibilants",  # s, z, x, ʃ, ʒ sounds
        "nasal_vowels",  # Nasal vowels (ã, ẽ, ĩ, õ, ũ)
    }
    if sentence.get("category") not in valid_categories:
        errors.append(
            f"Sentence {index}: Invalid category '{sentence.get('category')}'"
        )

    # Validate difficulty
    valid_difficulties = {"basic", "intermediate", "advanced"}
    if sentence.get("difficulty") not in valid_difficulties:
        errors.append(
            f"Sentence {index}: Invalid difficulty '{sentence.get('difficulty')}'"
        )

    return errors


def calculate_coverage(data: dict[str, Any], vocab: frozenset[str]) -> dict[str, Any]:
    """Calculate phoneme coverage statistics.

    Args:
        data: Parsed JSON data
        vocab: Valid phoneme vocabulary

    Returns:
        Dictionary with coverage statistics
    """
    all_phonemes = set()
    for sentence in data.get("sentences", []):
        phonemes = sentence.get("phonemes", "")
        # Exclude whitespace
        all_phonemes.update(c for c in phonemes if c not in (" ", "\t", "\n"))

    covered = all_phonemes & vocab
    missing = vocab - all_phonemes

    return {
        "total_vocab": len(vocab),
        "phonemes_covered": len(covered),
        "coverage_percent": (len(covered) / len(vocab) * 100) if vocab else 0,
        "covered_phonemes": sorted(covered),
        "missing_phonemes": sorted(missing),
    }


def validate_file(filepath: Path) -> dict[str, Any]:
    """Validate a synthetic benchmark data file.

    Args:
        filepath: Path to JSON file

    Returns:
        Dictionary with validation results
    """
    print(f"\n{'=' * 70}")
    print(f"Validating: {filepath.name}")
    print(f"{'=' * 70}")

    # Load file
    try:
        with open(filepath) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return {
            "valid": False,
            "errors": [f"Invalid JSON: {e}"],
            "filepath": str(filepath),
        }
    except FileNotFoundError:
        return {
            "valid": False,
            "errors": [f"File not found: {filepath}"],
            "filepath": str(filepath),
        }

    errors = []

    # Validate metadata
    errors.extend(validate_metadata(data))

    # Get language and vocab
    language = data.get("metadata", {}).get("language", "en-us")
    try:
        vocab = get_vocab_for_language(language)
    except ValueError as e:
        errors.append(str(e))
        return {
            "valid": False,
            "errors": errors,
            "filepath": str(filepath),
        }

    # Validate sentences
    if "sentences" not in data:
        errors.append("Missing 'sentences' section")
    else:
        for i, sentence in enumerate(data["sentences"]):
            errors.extend(validate_sentence(sentence, vocab, i))

    # Calculate coverage
    coverage = calculate_coverage(data, vocab)

    # Print results
    is_valid = len(errors) == 0

    if is_valid:
        print("✓ VALID - All checks passed!")
    else:
        print(f"✗ INVALID - Found {len(errors)} error(s):")
        for error in errors[:20]:  # Limit to first 20 errors
            print(f"  • {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")

    print("\nPhoneme Coverage:")
    print(f"  Total phonemes in vocab: {coverage['total_vocab']}")
    print(f"  Phonemes covered: {coverage['phonemes_covered']}")
    print(f"  Coverage: {coverage['coverage_percent']:.1f}%")

    if coverage["missing_phonemes"]:
        print(f"\nMissing phonemes ({len(coverage['missing_phonemes'])}):")
        print(f"  {' '.join(coverage['missing_phonemes'])}")

    # Category breakdown
    if "sentences" in data and is_valid:
        print("\nCategory Breakdown:")
        categories = {}
        for sentence in data["sentences"]:
            cat = sentence.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        for cat, count in sorted(categories.items()):
            print(f"  {cat:25} {count:3} sentences")

    return {
        "valid": is_valid,
        "errors": errors,
        "coverage": coverage,
        "filepath": str(filepath),
        "total_sentences": len(data.get("sentences", [])),
    }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate synthetic benchmark data")
    parser.add_argument(
        "files",
        nargs="*",
        help="Paths to synthetic data files (JSON)",
    )
    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Validate all *_synthetic.json files in benchmarks/data/",
    )

    args = parser.parse_args()

    # Find files to validate
    if args.all:
        data_dir = Path(__file__).parent / "data"
        files = sorted(data_dir.glob("*_synthetic.json"))
        if not files:
            print("No *_synthetic.json files found in benchmarks/data/")
            return 1
    elif args.files:
        files = [Path(f) for f in args.files]
    else:
        # Default: validate en_us_synthetic.json
        files = [Path(__file__).parent / "data" / "en_us_synthetic.json"]

    # Validate each file
    results = []
    for filepath in files:
        result = validate_file(filepath)
        results.append(result)

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    valid_count = sum(1 for r in results if r["valid"])
    total_count = len(results)

    print(f"Files validated: {total_count}")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {total_count - valid_count}")

    if valid_count == total_count:
        print("\n✓ All files are valid!")
        return 0
    else:
        print(f"\n✗ {total_count - valid_count} file(s) have errors")
        return 1


if __name__ == "__main__":
    sys.exit(main())
