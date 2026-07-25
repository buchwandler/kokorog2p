#!/usr/bin/env python3
"""Add metadata to Chinese synthetic dataset."""

import json
from datetime import date
from pathlib import Path

dataset_path = Path(__file__).parent / "data" / "zh_synthetic.json"

# Load existing data
with open(dataset_path) as f:
    sentences = json.load(f)

# Create dataset with metadata
dataset = {
    "metadata": {
        "version": "1.0",
        "language": "zh-cn",
        "created_date": str(date.today()),
        "description": "Chinese (Mandarin) synthetic benchmark dataset for kokorog2p",
        "phoneme_set": "kokoro",
        "phoneme_notation": "Zhuyin (Bopomofo)",
        "total_sentences": len(sentences),
        "coverage_notes": [
            "Uses Zhuyin (Bopomofo) phonetic notation, not IPA",
            "Includes all 21 Zhuyin initials (consonants)",
            "Includes all 16 basic Zhuyin finals (vowels/diphthongs)",
            "Includes 17 special final markers (compound finals)",
            "Covers all 5 Mandarin tones (1-5)",
            "Character-based phoneme system (no word-boundary spaces)",
            "Tone sandhi and erhua (儿化音) variations included",
        ],
    },
    "sentences": sentences,
}

# Save with metadata
with open(dataset_path, "w", encoding="utf-8") as f:
    json.dump(dataset, f, ensure_ascii=False, indent=2)

print(f"✓ Added metadata to {dataset_path}")
print(f"  Total sentences: {len(sentences)}")
print("  Language: zh-cn (Chinese Mandarin)")
print("  Phoneme notation: Zhuyin (Bopomofo)")
