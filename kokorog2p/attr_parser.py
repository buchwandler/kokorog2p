"""Robust attribute parser for span-based annotations.

This module provides a state-machine parser for annotation attributes that supports:
- Single quotes: key='value'
- Double quotes: key="value"
- Mixed quotes in same annotation
- Multiple attributes: key1="v1" key2='v2'
- Keys with hyphens and colons: xml:lang, voice-name
- Escape sequences: \\" and \\'
"""

from typing import NamedTuple


class ParsedAttr(NamedTuple):
    """A parsed attribute key-value pair."""

    key: str
    value: str


class AttrParseWarning(NamedTuple):
    """A warning from attribute parsing."""

    message: str
    position: int


def parse_attributes(text: str) -> tuple[dict[str, str], list[AttrParseWarning]]:
    """Parse annotation attributes from brace content.

    Supports:
    - key="value" (double quotes)
    - key='value' (single quotes)
    - Mixed quotes: key1="v1" key2='v2'
    - Keys with hyphens/colons: xml:lang, voice-name, ph
    - Escape sequences: \\" and \\'
    - Whitespace between pairs

    Args:
        text: The content between braces (e.g., 'ph="wɝːld" lang="en"')

    Returns:
        Tuple of (attributes_dict, warnings_list)

    Example:
        >>> parse_attributes('ph="hello" lang=\\'fr\\'')
        ({'ph': 'hello', 'lang': 'fr'}, [])
        >>> parse_attributes('xml:lang="en-US" voice-name="Amy"')
        ({'xml:lang': 'en-US', 'voice-name': 'Amy'}, [])
    """
    attrs: dict[str, str] = {}
    warnings: list[AttrParseWarning] = []
    i = 0
    n = len(text)

    while i < n:
        # Skip whitespace
        while i < n and text[i].isspace():
            i += 1
        if i >= n:
            break

        # Parse key
        key_start = i
        # Key: [A-Za-z_][A-Za-z0-9_:-]*
        if not (text[i].isalpha() or text[i] == "_"):
            warnings.append(
                AttrParseWarning(f"Expected key at position {i}, found '{text[i]}'", i)
            )
            # Skip to next space or =
            while i < n and text[i] not in (" ", "="):
                i += 1
            continue

        while i < n and (text[i].isalnum() or text[i] in ("_", "-", ":")):
            i += 1

        key = text[key_start:i]

        # Skip whitespace
        while i < n and text[i].isspace():
            i += 1

        # Expect '='
        if i >= n or text[i] != "=":
            warnings.append(
                AttrParseWarning(f"Expected '=' after key '{key}' at position {i}", i)
            )
            continue

        i += 1  # Skip '='

        # Skip whitespace
        while i < n and text[i].isspace():
            i += 1

        # Parse value
        if i >= n:
            warnings.append(
                AttrParseWarning(f"Expected value for key '{key}' at position {i}", i)
            )
            break

        # Check for quotes
        quote_char = None
        if text[i] in ('"', "'"):
            quote_char = text[i]
            i += 1

        value_start = i
        value_chars: list[str] = []

        if quote_char:
            # Parse quoted value
            while i < n:
                if text[i] == "\\":
                    # Escape sequence
                    if i + 1 < n:
                        next_char = text[i + 1]
                        if next_char == quote_char:
                            value_chars.append(quote_char)
                            i += 2
                            continue
                        elif next_char == "\\":
                            value_chars.append("\\")
                            i += 2
                            continue
                    # Not a recognized escape, keep the backslash
                    value_chars.append(text[i])
                    i += 1
                elif text[i] == quote_char:
                    # End of quoted value
                    i += 1
                    break
                else:
                    value_chars.append(text[i])
                    i += 1
            else:
                # Reached end without closing quote
                warnings.append(
                    AttrParseWarning(
                        f"Unclosed quote for key '{key}' starting at "
                        f"position {value_start - 1}",
                        value_start - 1,
                    )
                )
        else:
            # Unquoted value (read until whitespace or end)
            while i < n and not text[i].isspace():
                value_chars.append(text[i])
                i += 1

        value = "".join(value_chars)
        attrs[key.casefold()] = value

    return attrs, warnings


__all__ = ["parse_attributes", "ParsedAttr", "AttrParseWarning"]
