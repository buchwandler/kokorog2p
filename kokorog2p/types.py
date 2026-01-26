"""Type definitions for span-based phonemization.

This module provides dataclasses for offset-aware phonemization that supports
deterministic override application and per-span language switching.

All character offsets refer to indices in the clean_text (after markup removal).
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TokenSpan:
    """A token with character offset information.

    Attributes:
        text: The token text (extracted from clean_text).
        char_start: Start position in clean_text (inclusive).
        char_end: End position in clean_text (exclusive).
        lang: Optional language override for this token.
        extended_text: Optional expanded text for phonemization.
        meta: Additional metadata (rating, tag, etc.).
    """

    text: str
    char_start: int
    char_end: int
    lang: str | None = None
    extended_text: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate offsets."""
        if self.char_end < self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must be >= char_start ({self.char_start})"
            )
        if self.char_start < 0:
            raise ValueError(f"char_start must be >= 0, got {self.char_start}")


@dataclass
class OverrideSpan:
    """An annotation span that overrides phonemization.

    Attributes:
        char_start: Start position in clean_text (inclusive).
        char_end: End position in clean_text (exclusive).
        attrs: Attributes from the annotation (e.g., {"ph": "...", "lang": "..."}).
    """

    char_start: int
    char_end: int
    attrs: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate offsets."""
        if self.char_end < self.char_start:
            raise ValueError(
                f"char_end ({self.char_end}) must be >= char_start ({self.char_start})"
            )
        if self.char_start < 0:
            raise ValueError(f"char_start must be >= 0, got {self.char_start}")

    def overlaps(self, token: "TokenSpan") -> bool:
        """Check if this override overlaps with a token span."""
        return not (
            self.char_end <= token.char_start or self.char_start >= token.char_end
        )


@dataclass
class PhonemizeResult:
    """Result of span-aware phonemization.

    Attributes:
        clean_text: Text with markup removed (only words and whitespace).
        tokens: List of token spans with offset information.
        extended_text: Text after expansions used for phonemization.
        phonemes: Phoneme string (space-separated), or None if token_ids
            requested instead.
        token_ids: Token IDs for model input (numpy array), or None if
            phonemes requested.
        warnings: List of warning messages (alignment issues, unsupported
            symbols, etc.).
    """

    clean_text: str = ""
    tokens: list[TokenSpan] = field(default_factory=list)
    extended_text: str = ""
    phonemes: str = ""
    token_ids: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return self.phonemes or ""


__all__ = [
    "TokenSpan",
    "OverrideSpan",
    "PhonemizeResult",
]
