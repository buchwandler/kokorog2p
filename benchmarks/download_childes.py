#!/usr/bin/env python3
"""Download CHILDES IPA dataset from HuggingFace.

This script downloads the IPA-CHILDES-split dataset which contains
natural child-directed speech with IPA transcriptions from multiple backends.

Dataset source: https://huggingface.co/datasets/fdemelo/ipa-childes-split

Available languages:
  - de-DE (German - Germany)
  - en-GB (English - British)
  - en-US (English - American)
  - es-ES (Spanish - Spain)
  - fr-FR (French - France)
  - it-IT (Italian - Italy)
  - ja-JP (Japanese - Japan)
  - ko-KR (Korean - Korea)
  - pt-BR (Portuguese - Brazil)
  - pt-PT (Portuguese - Portugal)
  - yue-CN (Cantonese - China)
  - zh-CN (Mandarin Chinese - China)

Usage:
    # Download all languages
    python benchmarks/download_childes.py --all

    # Download specific languages
    python benchmarks/download_childes.py --languages en-GB en-US de-DE

    # Download with progress display
    python benchmarks/download_childes.py --languages en-GB --verbose
"""

import argparse
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

# Available languages in the dataset
AVAILABLE_LANGUAGES = [
    "de-DE",
    "en-GB",
    "en-US",
    "es-ES",
    "fr-FR",
    "it-IT",
    "ja-JP",
    "ko-KR",
    "pt-BR",
    "pt-PT",
    "yue-CN",
    "zh-CN",
]

# Base URL pattern
BASE_URL = "https://huggingface.co/datasets/fdemelo/ipa-childes-split/resolve/main/train/{lang}/data.csv"


def download_with_progress(url: str, output_path: Path, verbose: bool = False) -> bool:
    """Download file with optional progress display.

    Args:
        url: URL to download
        output_path: Path to save file
        verbose: Show progress

    Returns:
        True if successful, False otherwise
    """

    def progress_hook(block_num, block_size, total_size):
        """Display download progress."""
        if not verbose or total_size <= 0:
            return

        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size)
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)

        # Update progress on same line
        sys.stdout.write(
            f"  Progress: {percent:5.1f}% "
            f"({mb_downloaded:6.1f} MB / {mb_total:6.1f} MB)"
        )
        sys.stdout.flush()

    try:
        urlretrieve(url, output_path, reporthook=progress_hook if verbose else None)
        if verbose:
            print()  # New line after progress
        return True
    except (URLError, HTTPError) as e:
        if verbose:
            print()  # New line after progress
        print(f"  ✗ Download failed: {e}")
        return False


def download_language(language: str, output_dir: Path, verbose: bool = False) -> bool:
    """Download CHILDES data for a specific language.

    Args:
        language: Language code (e.g., "en-GB")
        output_dir: Output directory
        verbose: Show progress

    Returns:
        True if successful, False otherwise
    """
    # Create language directory
    lang_dir = output_dir / language
    lang_dir.mkdir(parents=True, exist_ok=True)

    # Construct URL
    url = BASE_URL.format(lang=language)
    output_path = lang_dir / "data.csv"

    # Check if already exists
    if output_path.exists():
        file_size = output_path.stat().st_size
        print(f"  ℹ Already exists: {output_path} ({file_size:,} bytes)")

        # Ask user if they want to re-download
        response = input(f"  Re-download {language}? [y/N]: ").strip().lower()
        if response not in ("y", "yes"):
            print(f"  ⊘ Skipping {language}")
            return True

    # Download
    print(f"  ↓ Downloading from: {url}")
    print(f"  → Saving to: {output_path}")

    success = download_with_progress(url, output_path, verbose)

    if success:
        file_size = output_path.stat().st_size
        print(
            f"  ✓ Downloaded {language}: {file_size:,} bytes "
            f"({file_size / (1024 * 1024):.1f} MB)"
        )
    else:
        # Clean up partial download
        if output_path.exists():
            output_path.unlink()

    return success


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Download CHILDES IPA dataset from HuggingFace",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Available languages:
{chr(10).join(f"  - {lang}" for lang in AVAILABLE_LANGUAGES)}

Examples:
  # Download English datasets
  %(prog)s --languages en-GB en-US

  # Download all languages
  %(prog)s --all

  # Download with progress display
  %(prog)s --languages en-GB --verbose
""",
    )

    parser.add_argument(
        "--languages",
        "-l",
        nargs="+",
        choices=AVAILABLE_LANGUAGES,
        help="Languages to download",
    )

    parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Download all available languages",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).parent / "ipa-childes-split",
        help="Output directory (default: benchmarks/ipa-childes-split)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show download progress",
    )

    args = parser.parse_args()

    # Determine which languages to download
    if args.all:
        languages = AVAILABLE_LANGUAGES
    elif args.languages:
        languages = args.languages
    else:
        parser.error("Please specify --languages or --all")

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("CHILDES IPA Dataset Downloader")
    print("=" * 80)
    print("Source: https://huggingface.co/datasets/fdemelo/ipa-childes-split")
    print(f"Output directory: {args.output}")
    print(f"Languages to download: {', '.join(languages)}")
    print()

    # Download each language
    results = {}
    for i, lang in enumerate(languages, 1):
        print(f"[{i}/{len(languages)}] Downloading {lang}...")
        success = download_language(lang, args.output, args.verbose)
        results[lang] = success
        print()

    # Print summary
    print("=" * 80)
    print("DOWNLOAD SUMMARY")
    print("=" * 80)

    successful = [lang for lang, success in results.items() if success]
    failed = [lang for lang, success in results.items() if not success]

    print(f"✓ Successful: {len(successful)}/{len(languages)}")
    for lang in successful:
        lang_dir = args.output / lang
        data_file = lang_dir / "data.csv"
        if data_file.exists():
            size_mb = data_file.stat().st_size / (1024 * 1024)
            print(f"  - {lang}: {size_mb:.1f} MB")

    if failed:
        print(f"\n✗ Failed: {len(failed)}")
        for lang in failed:
            print(f"  - {lang}")
        return 1

    print("\n✓ All downloads complete!")
    print(f"Data saved to: {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
