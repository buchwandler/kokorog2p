"""Native Northern Vietnamese G2P frontend."""

from .g2p import VietnameseAnalysis, VietnameseG2P
from .phonology import Phone
from .syllable import (
    InvalidVietnameseSyllable,
    VietnameseG2PError,
    VietnameseSyllable,
    VietnameseTone,
    is_vietnamese_syllable,
    parse_syllable,
)
from .unicode import (
    ToneExtraction,
    decompose_vietnamese,
    extract_tone,
    normalize_vietnamese,
    remove_tone_marks,
)


def phonemize_vi(text: str, **kwargs: object) -> str:
    """Phonemize Vietnamese text with a fresh native frontend."""
    return VietnameseG2P(**kwargs).phonemize(text)


__all__ = [
    "InvalidVietnameseSyllable",
    "Phone",
    "ToneExtraction",
    "VietnameseAnalysis",
    "VietnameseG2P",
    "VietnameseG2PError",
    "VietnameseSyllable",
    "VietnameseTone",
    "decompose_vietnamese",
    "extract_tone",
    "is_vietnamese_syllable",
    "normalize_vietnamese",
    "parse_syllable",
    "phonemize_vi",
    "remove_tone_marks",
]
