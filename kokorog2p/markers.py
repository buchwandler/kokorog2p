"""Marker-delimited helper for creating override spans.

This module provides a convenient way to mark text spans using delimiters
(e.g., @word@) and apply attributes to them, without requiring complex
markup syntax.

Example:
    >>> from kokorog2p.markers import parse_delimited, apply_marker_overrides
    >>> from kokorog2p import phonemize_to_result
    >>>
    >>> text = "Ich mag @New York@. @Hi@ Klaus."
    >>> clean_text, ranges, warnings = parse_delimited(text, marker="@")
    >>> # ranges = [(8, 16), (18, 20)]  # "New York" and "Hi"
    >>>
    >>> assignments = {
    ...     1: {"ph": "nuː jɔːk"},
    ...     2: {"lang": "en-us"},
    ... }
    >>> overrides = apply_marker_overrides(clean_text, ranges, assignments)
    >>> result = phonemize_to_result(clean_text, lang="de", overrides=overrides)
"""

import re

from kokorog2p.types import OverrideSpan


def parse_delimited(
    text: str,
    marker: str = "@",
    escape: str = "\\",
) -> tuple[str, list[tuple[int, int]], list[str]]:
    """Parse marker-delimited text to extract clean text and marked ranges.

    This function extracts text spans marked with a delimiter (e.g., @word@)
    and returns the clean text along with character offset ranges.

    Args:
        text: Input text with marker-delimited spans (e.g., "I like @coffee@").
        marker: Delimiter character to use for marking spans (default: "@").
        escape: Escape character for literal marker (default: "\\").

    Returns:
        Tuple of (clean_text, marked_ranges, warnings) where:
        - clean_text: Text with markers removed
        - marked_ranges: List of (char_start, char_end) tuples in clean_text
        - warnings: List of warning messages

    Rules:
        - Markers must come in pairs (opening and closing)
        - Unmatched markers generate warnings and are treated as literal text
        - Escaped markers (e.g., \\@) are treated as literal text
        - Nested markers are not supported and generate warnings

    Examples:
        >>> parse_delimited("I like @coffee@.")
        ('I like coffee.', [(7, 13)], [])

        >>> parse_delimited("I like @coffee@ and @tea@.")
        ('I like coffee and tea.', [(7, 13), (18, 21)], [])

        >>> parse_delimited("Email: user\\@example.com")
        ('Email: user@example.com', [], [])

        >>> parse_delimited("Unmatched @marker")
        ('Unmatched @marker', [], ['Unmatched opening marker at position 10'])

        >>> parse_delimited("Nested @outer @inner@ outer@")
        ('Nested outer inner outer', [(7, 23)],
         ['Nested markers detected at position 14'])
    """
    clean_parts: list[str] = []
    marked_ranges: list[tuple[int, int]] = []
    warnings: list[str] = []

    # Escape the marker and escape character for regex
    escaped_marker = re.escape(marker)
    escaped_escape = re.escape(escape)

    # Build regex pattern to match escaped markers or regular markers
    # This pattern matches either:
    # 1. Escaped marker (e.g., \@)
    # 2. Regular marker (e.g., @)
    pattern = f"({escaped_escape}{escaped_marker}|{escaped_marker})"

    current_pos = 0  # Position in clean_text
    text_pos = 0  # Position in original text
    in_marker = False
    marker_start_pos = -1
    marker_start_clean_pos = -1
    nesting_level = 0

    # Split by pattern and iterate
    parts = re.split(pattern, text)

    i = 0
    while i < len(parts):
        part = parts[i]

        # Check if this part is an escaped marker
        if part == f"{escape}{marker}":
            # Add literal marker to clean text
            clean_parts.append(marker)
            current_pos += len(marker)
            text_pos += len(part)

        # Check if this part is a marker
        elif part == marker:
            if not in_marker:
                # Opening marker
                in_marker = True
                marker_start_pos = text_pos
                marker_start_clean_pos = current_pos
                nesting_level += 1
            else:
                # Closing marker
                nesting_level -= 1

                if nesting_level == 0:
                    # Valid pair
                    marked_ranges.append((marker_start_clean_pos, current_pos))
                    in_marker = False
                    marker_start_pos = -1
                    marker_start_clean_pos = -1
                else:
                    # Nested marker - emit warning
                    warnings.append(f"Nested markers detected at position {text_pos}")

            text_pos += len(marker)

        else:
            # Regular text
            if in_marker and nesting_level > 1:
                # We're inside nested markers - count as part of marked text
                clean_parts.append(part)
                current_pos += len(part)
            else:
                # Regular text outside markers or in first level
                clean_parts.append(part)
                current_pos += len(part)

            text_pos += len(part)

        i += 1

    # Check for unmatched opening marker
    if in_marker:
        warnings.append(f"Unmatched opening marker at position {marker_start_pos}")

    clean_text = "".join(clean_parts)
    return clean_text, marked_ranges, warnings


def apply_marker_overrides(
    clean_text: str,
    marked_ranges: list[tuple[int, int]],
    assignments: list[dict[str, str]] | dict[int, dict[str, str]],
) -> list[OverrideSpan]:
    """Convert marked ranges and attribute assignments to OverrideSpan list.

    This function takes character ranges from parse_delimited() and applies
    attributes to create OverrideSpan objects for phonemization.

    Args:
        clean_text: Clean text (output from parse_delimited).
        marked_ranges: List of (char_start, char_end) tuples from parse_delimited.
        assignments: Attributes to assign to each marked range. Can be either:
            - List of dicts: Applied in order (must match length of marked_ranges)
            - Dict with 1-based indices: Applied by index number
                Example: {1: {"ph": "..."}, 2: {"lang": "..."}}

    Returns:
        List of OverrideSpan objects ready for phonemize_to_result.

    Raises:
        ValueError: If list assignments length doesn't match marked_ranges length,
            or if a referenced index is out of range.

    Examples:
        >>> ranges = [(7, 13), (18, 21)]
        >>> # Using list (in order)
        >>> assignments = [{"ph": "ˈkɔfi"}, {"lang": "en-us"}]
        >>> overrides = apply_marker_overrides("", ranges, assignments)

        >>> # Using dict with 1-based indices
        >>> assignments = {
        ...     1: {"ph": "ˈkɔfi"},
        ...     2: {"lang": "en-us"}
        ... }
        >>> overrides = apply_marker_overrides("", ranges, assignments)

        >>> # Selective assignment (only second range)
        >>> assignments = {2: {"lang": "en-us"}}
        >>> overrides = apply_marker_overrides("", ranges, assignments)
    """
    overrides: list[OverrideSpan] = []

    if isinstance(assignments, list):
        # List-based assignments (must match length)
        if len(assignments) != len(marked_ranges):
            raise ValueError(
                f"Assignment list length ({len(assignments)}) does not match "
                f"marked ranges length ({len(marked_ranges)})"
            )

        for (char_start, char_end), attrs in zip(
            marked_ranges, assignments, strict=False
        ):
            if attrs:  # Skip empty attribute dicts
                overrides.append(OverrideSpan(char_start, char_end, attrs))

    elif isinstance(assignments, dict):
        # Dict-based assignments (1-indexed)
        for idx, attrs in assignments.items():
            # Convert 1-based index to 0-based
            range_idx = idx - 1

            if range_idx < 0 or range_idx >= len(marked_ranges):
                raise ValueError(
                    f"Assignment index {idx} is out of range "
                    f"(valid: 1-{len(marked_ranges)})"
                )

            char_start, char_end = marked_ranges[range_idx]
            if attrs:  # Skip empty attribute dicts
                overrides.append(OverrideSpan(char_start, char_end, attrs))

    else:
        raise TypeError(
            f"Assignments must be list or dict, got {type(assignments).__name__}"
        )

    return overrides


__all__ = [
    "parse_delimited",
    "apply_marker_overrides",
]
