"""Span-based annotation processing for deterministic override application.

This module provides offset-based span processing for enabling deterministic
phoneme/language override application even with duplicates, punctuation, and
mixed languages.
"""

from typing import Literal

from kokorog2p.types import OverrideSpan, TokenSpan


def apply_overrides_to_tokens(
    tokens: list[TokenSpan],
    overrides: list[OverrideSpan],
    mode: Literal["snap", "strict"] = "snap",
) -> tuple[list[TokenSpan], list[str]]:
    """Apply override spans to token spans by character offset overlap.

    This is the deterministic core that applies phoneme/language overrides
    based on character offsets, handling duplicates and punctuation correctly.

    Args:
        tokens: List of token spans with char offsets in clean_text.
        overrides: List of override spans with attrs to apply.
        mode: Overlap handling mode:
            - "snap": Snap partial overlaps to full tokens (emit warning)
            - "strict": Skip partial overlaps (emit warning)

    Returns:
        Tuple of (modified_tokens, warnings)

    Overlap rules:
        - Exact match: override span == token span → apply to token
        - Full overlap: override contains multiple tokens → apply to all
        - Partial overlap: depends on mode
            - snap: apply to all intersecting tokens + warning
            - strict: skip override + warning
        - No overlap: skip override + warning

    Example:
        >>> tokens = [TokenSpan("Hello", 0, 5), TokenSpan("world", 6, 11)]
        >>> overrides = [OverrideSpan(0, 5, {"ph": "hɛloʊ"})]
        >>> apply_overrides_to_tokens(tokens, overrides)
        ([TokenSpan("Hello", 0, 5, meta={"ph": "hɛloʊ"}), ...], [])
    """
    warnings: list[str] = []
    modified_tokens = [
        TokenSpan(
            text=t.text,
            char_start=t.char_start,
            char_end=t.char_end,
            lang=t.lang,
            meta=dict(t.meta),  # Copy meta
        )
        for t in tokens
    ]

    for override in overrides:
        # Find all tokens that overlap with this override
        overlapping_indices: list[int] = []
        for i, token in enumerate(modified_tokens):
            if override.overlaps(token):
                overlapping_indices.append(i)

        if not overlapping_indices:
            # No tokens overlap this override span
            warnings.append(
                f"Override span ({override.char_start}, {override.char_end}) "
                f"does not overlap any tokens; skipping"
            )
            continue

        # Check if override exactly matches token boundaries
        first_idx = overlapping_indices[0]
        last_idx = overlapping_indices[-1]
        first_token = modified_tokens[first_idx]
        last_token = modified_tokens[last_idx]

        exact_match = (
            override.char_start == first_token.char_start
            and override.char_end == last_token.char_end
        )

        partial_overlap = (
            override.char_start > first_token.char_start
            or override.char_end < last_token.char_end
        )

        if partial_overlap and not exact_match:
            # Partial boundary overlap
            if mode == "strict":
                warnings.append(
                    f"Override span ({override.char_start}, {override.char_end}) "
                    f"partially overlaps token boundaries; skipping (strict mode)"
                )
                continue
            else:  # snap mode
                warnings.append(
                    f"Override span ({override.char_start}, {override.char_end}) "
                    f"partially overlaps token boundaries; snapping to tokens "
                    f"{first_idx}-{last_idx}"
                )

        # Apply override attributes to all overlapping tokens
        for idx in overlapping_indices:
            token = modified_tokens[idx]

            # Apply phoneme override if present
            if "ph" in override.attrs:
                token.meta["ph"] = override.attrs["ph"]
                token.meta["rating"] = 5  # User-provided override

            # Apply language override if present
            if "lang" in override.attrs:
                token.lang = override.attrs["lang"]

            # Store other attributes in meta
            for key, value in override.attrs.items():
                if key not in ("ph", "lang"):
                    token.meta[key] = value

    return modified_tokens, warnings


def tokens_to_text_with_spacing(tokens: list[TokenSpan]) -> str:
    """Reconstruct text from tokens, preserving original spacing.

    Uses char_start/char_end to determine spacing between tokens.

    Args:
        tokens: List of token spans.

    Returns:
        Reconstructed text string.
    """
    if not tokens:
        return ""

    parts: list[str] = []
    for i, token in enumerate(tokens):
        parts.append(token.text)

        # Add spacing before next token if needed
        if i + 1 < len(tokens):
            next_token = tokens[i + 1]
            gap = next_token.char_start - token.char_end
            if gap > 0:
                parts.append(" " * gap)

    return "".join(parts)


__all__ = [
    "apply_overrides_to_tokens",
    "tokens_to_text_with_spacing",
]
