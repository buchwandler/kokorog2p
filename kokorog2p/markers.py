"""Marker-delimited helper for creating override spans.

This module provides a convenient way to mark text spans using delimiters
(e.g., @word@) and apply attributes to them, without requiring complex
markup syntax.

Example:
    >>> from kokorog2p.markers import parse_delimited, apply_marker_overrides
    >>> from kokorog2p import phonemize
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
    >>> result = phonemize(clean_text, language="de", overrides=overrides)
"""

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
        ('Nested outer inner outer', [(7, 13), (18, 24)],
         ['Nested markers detected at position 7'])
    """
    clean_parts: list[str] = []
    marked_ranges: list[tuple[int, int]] = []
    warnings: list[str] = []

    marker_positions: list[int] = []
    i = 0
    while i < len(text):
        if text.startswith(escape, i) and i + len(escape) < len(text):
            i += len(escape) + 1
            continue
        if text.startswith(marker, i):
            marker_positions.append(i)
            i += len(marker)
            continue
        i += 1

    current_pos = 0
    in_marker = False
    marker_start_pos = -1
    marker_start_clean_pos = -1
    marker_index = 0

    i = 0
    while i < len(text):
        if text.startswith(escape, i) and i + len(escape) < len(text):
            next_char = text[i + len(escape)]
            if next_char == marker or next_char == escape:
                clean_parts.append(next_char)
                current_pos += 1
                i += len(escape) + 1
                continue

        if marker_index < len(marker_positions) and i == marker_positions[marker_index]:
            if not in_marker:
                in_marker = True
                marker_start_pos = i
                marker_start_clean_pos = current_pos
            else:
                marked_ranges.append((marker_start_clean_pos, current_pos))
                in_marker = False
                next_marker = (
                    marker_positions[marker_index + 1]
                    if marker_index + 1 < len(marker_positions)
                    else None
                )
                if next_marker is not None:
                    between = text[i + len(marker) : next_marker]
                    if between and not any(ch.isspace() for ch in between):
                        warnings.append(
                            f"Nested markers detected at position {marker_start_pos}"
                        )
                marker_start_pos = -1
                marker_start_clean_pos = -1
            marker_index += 1
            i += len(marker)
            continue

        clean_parts.append(text[i])
        current_pos += 1
        i += 1

    clean_text = "".join(clean_parts)

    if in_marker:
        warnings.append(f"Unmatched opening marker at position {marker_start_pos}")
        insert_pos = max(0, min(marker_start_clean_pos, len(clean_text)))
        clean_text = clean_text[:insert_pos] + marker + clean_text[insert_pos:]

    sanitized_ranges: list[tuple[int, int]] = []
    last_end = 0
    for start, end in sorted(marked_ranges, key=lambda r: (r[0], r[1])):
        start = max(0, min(start, len(clean_text)))
        end = max(0, min(end, len(clean_text)))
        if end < start:
            warnings.append(f"Invalid marker range ({start}, {end}); skipping")
            continue
        if start < last_end:
            warnings.append(
                f"Overlapping marker ranges detected at ({start}, {end}); skipping"
            )
            continue
        sanitized_ranges.append((start, end))
        last_end = end

    return clean_text, sanitized_ranges, warnings


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
        List of OverrideSpan objects ready for phonemize.

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
