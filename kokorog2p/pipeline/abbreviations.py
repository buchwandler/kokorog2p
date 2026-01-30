"""Base framework for abbreviation expansion in the G2P pipeline.

This module provides the infrastructure for expanding abbreviations before
phonemization. It supports:
- Simple 1:1 mappings (Prof. → Professor)
- Context-aware expansions (St. → Street/Saint based on context)
- Case-insensitive matching
- Word boundary detection
- Optional numeric/context guards for tricky abbreviations (e.g., No., in.)
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from re import Pattern


class AbbreviationContext(Enum):
    """Context types for disambiguating abbreviations."""

    DEFAULT = "default"  # Use default expansion
    TITLE = "title"  # Title/honorific (Dr. Smith)
    PLACE = "place"  # Place name (Main St.)
    TIME = "time"  # Time-related (3 P.M.)
    ACADEMIC = "academic"  # Academic degree (Ph.D.)
    RELIGIOUS = "religious"  # Religious context (St. Peter)


@dataclass
class AbbreviationEntry:
    """A single abbreviation with its expansion(s).

    Attributes:
        abbreviation: The abbreviated form (e.g., "Prof.")
        expansion: Default expansion (e.g., "Professor")
        context_expansions: Optional dict of context-specific expansions
        case_sensitive: Whether matching should be case-sensitive
        description: Human-readable description of the abbreviation
        only_if_preceded_by: Optional regex that must match the text immediately
            before the abbreviation match (typically anchored with $).
        only_if_followed_by: Optional regex that must match the text immediately
            after the abbreviation match (typically anchored with ^ or using
            atch()).
    """

    abbreviation: str
    expansion: str
    context_expansions: dict[AbbreviationContext, str] | None = None
    case_sensitive: bool = False
    description: str = ""
    only_if_preceded_by: str | Pattern[str] | None = None
    only_if_followed_by: str | Pattern[str] | None = None

    def get_expansion(self, context: AbbreviationContext | None = None) -> str:
        """Get the appropriate expansion for the given context.

        Args:
            context: The context type, or None for default

        Returns:
            The expanded form
        """
        if context and self.context_expansions and context in self.context_expansions:
            return self.context_expansions[context]
        return self.expansion


class ContextDetector:
    """Detects context for abbreviations based on surrounding text."""

    def __init__(self):
        """Initialize context detector with pattern matchers."""
        # Patterns for detecting place names (street, avenue, etc.)
        # Match addresses like "123 Main", "100 N. Main", "50 North Elm"
        self.place_indicators = re.compile(
            # Address number, optional direction abbrev
            r"\b\d+\s+(?:[A-Z]\.\s+)?\w+(?:\s+\w+)*$",
            re.IGNORECASE,
        )

        # Patterns for detecting titles (before names)
        self.title_indicators = re.compile(
            r"^(?:\w+\s+)*[A-Z][a-z]+",  # Followed by capitalized name
        )

        # Patterns for detecting time (with numbers)
        self.time_indicators = re.compile(
            r"\b\d{1,2}(?::\d{2})?\s*$",  # Preceded by time (3:00, 5)
            re.IGNORECASE,
        )

    def detect_context(
        self, abbreviation: str, before: str, after: str
    ) -> AbbreviationContext:
        """Detect the context of an abbreviation.

        Args:
            abbreviation: The abbreviation itself
            before: Text before the abbreviation
            after: Text after the abbreviation

        Returns:
            The detected context type

        Note:
            St. abbreviation uses multi-signal detection for robustness:
            - Priority 1: Saint/city name recognition (highest confidence)
            - Priority 2: House number pattern in close proximity (~30 chars)
            - Priority 3: Default to "Saint" for unknown names

            Examples:
                "123 Main St." → Street (house number pattern)
                "St. Louis" → Saint (city name recognized)
                "Visit 123 St. Louis Ave" → Saint (name wins over distant number)
                "born in 1850, St. Peter" → Saint (name + distant number)
        """
        # Check for time context (3 P.M., 5 A.M.)
        if self.time_indicators.search(before):
            return AbbreviationContext.TIME

        # Special handling for St. abbreviation (Saint vs Street)
        # Uses multi-signal approach for robust detection
        if abbreviation.lower() in ["st.", "st"]:
            # PRIORITY 1: Check for saint/city name (HIGHEST CONFIDENCE)
            if after:
                # Common saint names
                saint_names = {
                    "peter",
                    "paul",
                    "john",
                    "mary",
                    "patrick",
                    "francis",
                    "joseph",
                    "michael",
                    "george",
                    "luke",
                    "mark",
                    "matthew",
                    "thomas",
                    "james",
                    "anthony",
                    "andrew",
                }

                # Common city names that start with St.
                city_names = {
                    "louis",
                    "paul",
                    "petersburg",
                    "augustine",
                    "helena",
                    "cloud",
                    "albans",
                    "andrews",
                }

                # Get first word and clean it (remove possessives, punctuation)
                first_word = after.strip().split()[0].lower() if after.strip() else ""
                first_word = first_word.rstrip("'s.,;:!?")

                if first_word in saint_names or first_word in city_names:
                    return AbbreviationContext.RELIGIOUS

            # PRIORITY 2: Check for house number pattern (CLOSE PROXIMITY)
            # Only check last 30 characters to avoid distant numbers
            # Pattern: "[number] [optional direction] [street name]"
            # Examples: "123 Main", "456 N. Oak", "10 Park"
            proximity_limit = 30
            recent_text = (
                before[-proximity_limit:] if len(before) > proximity_limit else before
            )

            # Special case: Ordinal numbers directly before St. = Street
            # "5th St." "42nd St." "3rd St."
            ordinal_street_pattern = re.compile(
                r"\d+(?:st|nd|rd|th)\s*$", re.IGNORECASE
            )
            if ordinal_street_pattern.search(recent_text):
                return AbbreviationContext.PLACE

            # Match house number followed by optional direction and street
            # Catches: "123 Main St." "456 N. Oak St."
            # But NOT: "born in 1850, St." (too far away)
            house_number_pattern = re.compile(
                # Number + optional direction + capitalized word
                r"\d+\s+(?:[NSEW]\.?\s+)?[A-Z]\w*\s*$",
                re.IGNORECASE,
            )

            if house_number_pattern.search(recent_text):
                return AbbreviationContext.PLACE

            # PRIORITY 3: Default to religious (Saint)
            return AbbreviationContext.RELIGIOUS

        # Check for place context for other abbreviations (Ave., Rd., Blvd., etc.)
        if self.place_indicators.search(before):
            return AbbreviationContext.PLACE

        # Check for title context (Dr. Smith, Prof. Johnson)
        if after and self.title_indicators.match(after):
            return AbbreviationContext.TITLE

        return AbbreviationContext.DEFAULT


class AbbreviationExpander(ABC):
    """Abstract base class for language-specific abbreviation expanders."""

    def __init__(
        self,
        enable_context_detection: bool = True,
    ):
        """Initialize the abbreviation expander.

        Args:
            enable_context_detection: Whether to use context-aware expansion
        """
        self.entries: dict[str, AbbreviationEntry] = {}
        self.enable_context_detection = enable_context_detection
        self.context_detector = ContextDetector() if enable_context_detection else None
        self._initialize_abbreviations()

    @abstractmethod
    def _initialize_abbreviations(self) -> None:
        """Initialize language-specific abbreviations.

        Subclasses must implement this to populate self.entries.
        """
        pass

    def add_abbreviation(self, entry: AbbreviationEntry) -> None:
        """Add an abbreviation entry.

        Args:
            entry: The abbreviation entry to add
        """
        key = entry.abbreviation if entry.case_sensitive else entry.abbreviation.lower()
        self.entries[key] = entry

    def remove_abbreviation(
        self, abbreviation: str, case_sensitive: bool = False
    ) -> bool:
        """Remove an abbreviation entry.

        Args:
            abbreviation: The abbreviation to remove (e.g., "Dr.")
            case_sensitive: Whether to match case-sensitively

        Returns:
            True if the abbreviation was found and removed, False otherwise
        """
        key = abbreviation if case_sensitive else abbreviation.lower()
        if key in self.entries:
            del self.entries[key]
            return True
        return False

    def has_abbreviation(self, abbreviation: str, case_sensitive: bool = False) -> bool:
        """Check if an abbreviation exists.

        Args:
            abbreviation: The abbreviation to check (e.g., "Dr.")
            case_sensitive: Whether to match case-sensitively

        Returns:
            True if the abbreviation exists, False otherwise
        """
        key = abbreviation if case_sensitive else abbreviation.lower()
        return key in self.entries

    def get_abbreviation(
        self, abbreviation: str, case_sensitive: bool = False
    ) -> AbbreviationEntry | None:
        """Get an abbreviation entry.

        Args:
            abbreviation: The abbreviation to retrieve (e.g., "Dr.")
            case_sensitive: Whether to match case-sensitively

        Returns:
            The abbreviation entry if found, None otherwise
        """
        key = abbreviation if case_sensitive else abbreviation.lower()
        return self.entries.get(key)

    def expand(self, text: str) -> str:
        """Expand all abbreviations in the text.

        Args:
            text: Input text containing abbreviations

        Returns:
            Text with abbreviations expanded
        """
        # Process abbreviations in order of length (longest first)
        # This prevents "Ph.D." from being processed as "Ph." + "D."
        sorted_abbrevs = sorted(self.entries.keys(), key=lambda x: len(x), reverse=True)

        for abbrev_key in sorted_abbrevs:
            entry = self.entries[abbrev_key]
            text = self._expand_single(text, entry)

        return text

    def _expand_single(self, text: str, entry: AbbreviationEntry) -> str:
        """Expand a single abbreviation in the text.

        Args:
            text: Input text
            entry: The abbreviation entry to expand

        Returns:
            Text with this abbreviation expanded
        """
        # Build regex pattern with word boundaries
        # For abbrevs with '.', match at word end or before punctuation
        abbrev = re.escape(entry.abbreviation)
        if entry.abbreviation.endswith("."):
            # Match abbreviation followed by space, punctuation, or end of string
            pattern = rf"\b{abbrev}(?=\s|[,;:!?]|$)"
        else:
            # Standard word boundary matching
            pattern = rf"\b{abbrev}\b"

        flags = 0 if entry.case_sensitive else re.IGNORECASE

        # Use a replacement function to support context detection
        def replacer(match: re.Match) -> str:
            start, end = match.span()

            # Optional guard: require something BEFORE the abbreviation.
            # Intended for units like "in." / "ft." / "oz." to
            # only expand after numbers:
            #   "10.0 in." -> "10.0 inch"
            #   "Wizard of Oz." (NOT preceded by a number) -> unchanged
            if entry.only_if_preceded_by:
                pat = entry.only_if_preceded_by
                if isinstance(pat, str):
                    pat = re.compile(pat)
                # Only check a short window for speed and to encourage
                # end-anchored patterns.
                window = 80
                before_slice = text[max(0, start - window) : start]
                if not pat.search(before_slice):
                    return match.group(0)

            # Optional guard: require something AFTER the abbreviation.
            # Intended for things like "No." to only expand when followed by digits:
            #   "No." -> unchanged
            #   "No. 244" -> "Number 244"
            if entry.only_if_followed_by:
                pat = entry.only_if_followed_by
                if isinstance(pat, str):
                    pat = re.compile(pat)
                if not pat.match(text, end):
                    return match.group(0)

            if not self.enable_context_detection or not self.context_detector:
                return entry.expansion

            # Get surrounding context
            before = text[:start].strip()
            after = text[end:].strip()

            # Detect context and get appropriate expansion
            context = self.context_detector.detect_context(match.group(), before, after)
            return entry.get_expansion(context)

        return re.sub(pattern, replacer, text, flags=flags)

    def get_abbreviations_list(self) -> list[str]:
        """Get a list of all supported abbreviations.

        Returns:
            List of abbreviation strings
        """
        return [entry.abbreviation for entry in self.entries.values()]

    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.__class__.__name__}(abbreviations={len(self.entries)})"
