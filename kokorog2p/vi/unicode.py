"""Unicode-safe Vietnamese orthography helpers.

Vietnamese tones are combining marks, so extraction is intentionally performed
on NFD text and all public orthography is returned in NFC.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .syllable import VietnameseTone

TONE_MARKS: dict[str, str] = {
    "\u0300": "huyen",
    "\u0309": "hoi",
    "\u0303": "nga",
    "\u0301": "sac",
    "\u0323": "nang",
}
QUALITY_MARKS = frozenset(("\u0306", "\u0302", "\u031b"))
VIETNAMESE_LETTERS = frozenset("aăâbcdđeêghiklmnoôơpqrstuvwxyz")
VIETNAMESE_VOWELS = frozenset("aăâeêioôơuưy")


class VietnameseG2PError(Exception):
    """Base exception for Vietnamese frontend errors."""


class InvalidVietnameseSyllable(VietnameseG2PError, ValueError):
    """Raised when Vietnamese orthography cannot be parsed safely."""


@dataclass(frozen=True)
class ToneExtraction:
    """Tone-less NFC orthography and its named lexical tone."""

    normalized: str
    tone_name: str
    mark: str | None = None

    @property
    def tone(self) -> VietnameseTone:
        """Return the public named tone enum lazily to avoid an import cycle."""
        from .syllable import VietnameseTone

        return VietnameseTone(self.tone_name)

    def __iter__(self):
        """Allow ``orthography, tone = extract_tone(...)`` for convenience."""
        yield self.normalized
        yield self.tone


def normalize_vietnamese(text: str) -> str:
    """Normalize Vietnamese text to NFC without changing its source offsets."""
    if not isinstance(text, str):
        raise TypeError(f"Vietnamese text must be str, got {type(text).__name__}")
    if any(unicodedata.category(char) == "Cs" for char in text):
        raise InvalidVietnameseSyllable("Vietnamese text contains an invalid surrogate")
    return unicodedata.normalize("NFC", text)


def decompose_vietnamese(text: str) -> str:
    """Return the canonical NFD representation used for mark inspection."""
    return unicodedata.normalize("NFD", normalize_vietnamese(text))


def extract_tone(text: str) -> ToneExtraction:
    """Extract one lexical tone mark while retaining vowel-quality marks.

    The input may be NFC or NFD. More than one lexical mark is malformed and
    raises instead of selecting an arbitrary tone.
    """
    nfd = decompose_vietnamese(text)
    marks = [char for char in nfd if char in TONE_MARKS]
    if len(marks) > 1:
        raise InvalidVietnameseSyllable(
            f"Vietnamese syllable has multiple lexical tone marks: {''.join(marks)!r}"
        )
    if marks:
        mark_index = next(index for index, char in enumerate(nfd) if char in TONE_MARKS)
        base_index = mark_index - 1
        while base_index >= 0 and nfd[base_index] in QUALITY_MARKS:
            base_index -= 1
        if base_index < 0 or nfd[base_index].casefold() not in VIETNAMESE_VOWELS:
            raise InvalidVietnameseSyllable(
                "Vietnamese lexical tone mark must attach to a vowel"
            )
    tone_name = TONE_MARKS[marks[0]] if marks else "ngang"
    without_tone = "".join(char for char in nfd if char not in TONE_MARKS)
    return ToneExtraction(
        normalized=unicodedata.normalize("NFC", without_tone),
        tone_name=tone_name,
        mark=marks[0] if marks else None,
    )


def remove_tone_marks(text: str) -> str:
    """Return NFC Vietnamese orthography without lexical tone marks."""
    return extract_tone(text).normalized


def tone_name(text: str) -> str:
    """Return the named tone value for one orthographic unit."""
    return extract_tone(text).tone_name


def is_vietnamese_letter(char: str) -> bool:
    """Return whether a character belongs to the Vietnamese alphabet."""
    if len(char) != 1:
        return False
    return char.casefold() in VIETNAMESE_LETTERS


def is_vietnamese_combining_mark(char: str) -> bool:
    """Return whether a mark is a Vietnamese quality or lexical mark."""
    return char in TONE_MARKS or char in QUALITY_MARKS


__all__ = [
    "QUALITY_MARKS",
    "TONE_MARKS",
    "InvalidVietnameseSyllable",
    "ToneExtraction",
    "VietnameseG2PError",
    "decompose_vietnamese",
    "extract_tone",
    "is_vietnamese_combining_mark",
    "is_vietnamese_letter",
    "normalize_vietnamese",
    "remove_tone_marks",
    "tone_name",
]
