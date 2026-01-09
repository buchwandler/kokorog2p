"""Core data models for the universal G2P pipeline.

This module defines the rich data structures used throughout the pipeline to track
text normalization, tokenization, and phonemization with full provenance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from kokorog2p.token import GToken


class PhonemeSource(Enum):
    """Source of a phoneme transcription."""

    # Lexicon sources (rated by quality)
    LEXICON_GOLD = "lexicon_gold"  # Rating 4-5, highest quality
    LEXICON_SILVER = "lexicon_silver"  # Rating 3, good quality
    LEXICON_BRONZE = "lexicon_bronze"  # Rating 2, acceptable quality
    LEXICON_UNKNOWN = "lexicon_unknown"  # Rating 0-1, low quality

    # Fallback sources
    ESPEAK = "espeak"  # eSpeak NG fallback
    GRUUT = "gruut"  # Gruut fallback
    GORUUT = "goruut"  # Go-based Gruut

    # Rule-based sources
    RULE_BASED = "rule_based"  # Language-specific rules
    PYPINYIN = "pypinyin"  # Chinese pypinyin
    G2PK = "g2pk"  # Korean g2pK
    PYOPENJTALK = "pyopenjtalk"  # Japanese pyopenjtalk
    CUTLET = "cutlet"  # Japanese Cutlet
    PHONIKUD = "phonikud"  # Hebrew phonikud

    # Special sources
    PUNCTUATION = "punctuation"  # Punctuation mapping
    UNKNOWN = "unknown"  # Source unknown or not yet determined

    @classmethod
    def from_rating(cls, rating: int | None) -> "PhonemeSource":
        """Convert a numeric rating to a lexicon source type.

        Args:
            rating: Numeric rating (0-5) or None

        Returns:
            Corresponding PhonemeSource enum value
        """
        if rating is None:
            return cls.LEXICON_UNKNOWN
        if rating >= 4:
            return cls.LEXICON_GOLD
        if rating == 3:
            return cls.LEXICON_SILVER
        if rating == 2:
            return cls.LEXICON_BRONZE
        return cls.LEXICON_UNKNOWN

    @property
    def display_name(self) -> str:
        """Get a human-readable display name."""
        return self.value.replace("_", " ").title()

    @property
    def is_lexicon(self) -> bool:
        """Check if this source is from a lexicon."""
        return self.value.startswith("lexicon_")

    @property
    def is_fallback(self) -> bool:
        """Check if this source is a fallback method."""
        return self in (self.ESPEAK, self.GRUUT, self.GORUUT)

    @property
    def is_rule_based(self) -> bool:
        """Check if this source is rule-based."""
        return self in (
            self.RULE_BASED,
            self.PYPINYIN,
            self.G2PK,
            self.PYOPENJTALK,
            self.CUTLET,
            self.PHONIKUD,
        )


@dataclass
class NormalizationStep:
    """A single normalization transformation applied to text.

    Tracks what changed, where it changed, and why it changed.
    """

    rule_name: str  # e.g., "apostrophe", "quote", "ellipsis"
    position: int  # Character position in original text
    original: str  # Original character(s)
    normalized: str  # Normalized character(s)
    context: str | None = None  # Optional context for debugging

    def __str__(self) -> str:
        """Format as a readable string."""
        ctx = f" ({self.context})" if self.context else ""
        orig = self.original
        norm = self.normalized
        return f"{self.rule_name:15} @ {self.position:3}: {orig!r} → {norm!r}{ctx}"


@dataclass
class ProcessingToken:
    """A token with full processing metadata and provenance.

    This is the rich internal representation used during pipeline processing.
    It can be converted to a GToken for backward compatibility.
    """

    # Core text information
    text: str  # Original token text (after normalization)
    normalized_text: str | None = None  # Further normalized form if different

    # Position tracking
    char_start: int = 0  # Start position in original text
    char_end: int = 0  # End position in original text

    # Quote nesting depth (for proper quote matching)
    quote_depth: int = 0

    # POS tagging
    pos_tag: str = ""  # Part-of-speech tag

    # Phoneme information
    phoneme: str | None = None
    phoneme_source: PhonemeSource | None = None
    phoneme_rating: int | None = None  # 0-5 for lexicon sources

    # Provenance tracking
    normalizations: list[NormalizationStep] = field(default_factory=list)

    # Language-specific metadata (e.g., pitch accent for Japanese, mora timing)
    language_metadata: dict[str, Any] = field(default_factory=dict)

    # Whitespace handling
    whitespace: str = " "

    def to_gtoken(self) -> GToken:
        """Convert to a GToken for backward compatibility.

        Preserves all information in the extension dictionary for debugging.
        """
        token = GToken(
            text=self.text,
            tag=self.pos_tag,
            whitespace=self.whitespace,
            phonemes=self.phoneme,
            rating=str(self.phoneme_rating)
            if self.phoneme_rating is not None
            else None,
        )

        # Store rich metadata in extension dict
        if self.phoneme_source:
            token.set("phoneme_source", self.phoneme_source.value)

        if self.char_start > 0 or self.char_end > 0:
            token.set("char_start", self.char_start)
            token.set("char_end", self.char_end)

        if self.quote_depth > 0:
            token.set("quote_depth", self.quote_depth)

        if self.normalized_text and self.normalized_text != self.text:
            token.set("normalized_text", self.normalized_text)

        if self.normalizations:
            token.set("normalizations", [str(n) for n in self.normalizations])

        if self.language_metadata:
            for key, value in self.language_metadata.items():
                token.set(key, value)

        return token

    @classmethod
    def from_gtoken(cls, token: GToken) -> "ProcessingToken":
        """Create a ProcessingToken from a GToken.

        Used for migrating existing code incrementally.
        """
        phoneme_source = None
        if token.get("phoneme_source"):
            try:
                phoneme_source = PhonemeSource(token.get("phoneme_source"))
            except ValueError:
                phoneme_source = PhonemeSource.UNKNOWN

        phoneme_rating = None
        if token.rating:
            try:
                phoneme_rating = int(token.rating)
            except (ValueError, TypeError):
                pass

        return cls(
            text=token.text,
            normalized_text=token.get("normalized_text"),
            char_start=token.get("char_start", 0),
            char_end=token.get("char_end", 0),
            quote_depth=token.get("quote_depth", 0),
            pos_tag=token.tag,
            phoneme=token.phonemes,
            phoneme_source=phoneme_source,
            phoneme_rating=phoneme_rating,
            whitespace=token.whitespace,
        )

    def debug_repr(self) -> str:
        """Create a debug string representation.

        Format: text → phoneme [source:rating] pos=TAG depth=N
        """
        parts = [f"{self.text:15}"]

        if self.phoneme:
            parts.append(f" → {self.phoneme:15}")
        else:
            parts.append(" " * 18)

        if self.phoneme_source:
            source_str = f"[{self.phoneme_source.value:15}"
            if self.phoneme_rating is not None:
                source_str += f":{self.phoneme_rating}]"
            else:
                source_str += " ]"
            parts.append(source_str)
        else:
            parts.append(" " * 18)

        if self.pos_tag:
            parts.append(f" pos={self.pos_tag:5}")

        if self.quote_depth > 0:
            parts.append(f" depth={self.quote_depth}")

        return "".join(parts)


@dataclass
class ProcessedText:
    """The result of processing text through the G2P pipeline.

    Contains the original text, normalized text, tokens with full provenance,
    and a log of all normalization steps.
    """

    original: str  # Original input text
    normalized: str  # Fully normalized text
    tokens: list[ProcessingToken]  # Rich tokens with metadata
    normalization_log: list[NormalizationStep] = field(default_factory=list)

    def to_gtokens(self) -> list[GToken]:
        """Convert all tokens to GToken format for backward compatibility."""
        return [token.to_gtoken() for token in self.tokens]

    def render_debug(self, show_normalizations: bool = True) -> str:
        """Render a human-readable debug view of the processing.

        Args:
            show_normalizations: Include normalization log in output

        Returns:
            Formatted debug string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"Original:    {self.original}")
        lines.append(f"Normalized:  {self.normalized}")
        lines.append("=" * 80)
        lines.append("")
        lines.append("Tokens:")
        lines.append("-" * 80)

        for token in self.tokens:
            lines.append(f"  {token.debug_repr()}")

        if show_normalizations and self.normalization_log:
            lines.append("")
            lines.append("Normalizations:")
            lines.append("-" * 80)
            for step in self.normalization_log:
                lines.append(f"  {step}")

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation shows the normalized text."""
        return self.normalized
