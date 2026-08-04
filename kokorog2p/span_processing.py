"""Span-based annotation processing for deterministic override application.

This module provides offset-based span processing for enabling deterministic
phoneme/language override application even with duplicates, punctuation, and
mixed languages.
"""

from collections.abc import Sequence
from typing import Literal

from kokorog2p.integrations import coerce_override_spans
from kokorog2p.types import TokenSpan


def apply_overrides_to_tokens(
    tokens: list[TokenSpan],
    overrides: Sequence[object],
    mode: Literal["snap", "strict"] = "snap",
) -> tuple[list[TokenSpan], list[str]]:
    def _format_token(token: TokenSpan) -> str:
        lang = f" lang='{token.lang}'" if token.lang else ""
        return f"'{token.text}' [{token.char_start}:{token.char_end}]{lang}"

    warnings: list[str] = []
    modified_tokens = [
        TokenSpan(
            text=t.text,
            char_start=t.char_start,
            char_end=t.char_end,
            lang=t.lang,
            extended_text=t.extended_text,
            meta=dict(t.meta),
        )
        for t in tokens
    ]

    # Normalize structurally compatible spans before applying them.
    normalized_overrides = sorted(
        coerce_override_spans(overrides), key=lambda o: (o.char_start, o.char_end)
    )

    for override in normalized_overrides:
        overlapping_indices: list[int] = [
            i
            for i, token in enumerate(modified_tokens)
            if not (
                override.char_end <= token.char_start
                or override.char_start >= token.char_end
            )
        ]

        if not overlapping_indices:
            warnings.append(
                f"[OVERRIDE] span [{override.char_start}:{override.char_end}] "
                "does not overlap any tokens; skipping"
            )
            continue

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
            if mode == "strict":
                warnings.append(
                    f"[OVERRIDE] span [{override.char_start}:{override.char_end}] "
                    "partially overlaps token boundaries "
                    f"(first {_format_token(first_token)}, last "
                    f"{_format_token(last_token)}); skipping (strict mode)"
                )
                continue
            warnings.append(
                f"[OVERRIDE] span [{override.char_start}:{override.char_end}] "
                "partially overlaps token boundaries "
                f"(first {_format_token(first_token)}, last "
                f"{_format_token(last_token)}); snapping to tokens "
                f"{first_idx}-{last_idx}"
            )

        # ---- NEW: if 'ph' spans multiple tokens, merge into one token ----
        if "ph" in override.attrs and first_idx != last_idx:
            merged_text = " ".join(
                t.text for t in modified_tokens[first_idx : last_idx + 1]
            )
            merged = TokenSpan(
                text=merged_text,
                char_start=first_token.char_start,
                char_end=last_token.char_end,
                lang=first_token.lang,
                extended_text=None,
                meta=dict(first_token.meta),
            )

            # Apply attrs to merged token
            merged.meta["ph"] = override.attrs["ph"]
            merged.meta["rating"] = 5
            if "lang" in override.attrs:
                merged.lang = override.attrs["lang"]

            for key, value in override.attrs.items():
                if key not in ("ph", "lang"):
                    merged.meta[key] = value

            # Replace the range with the merged token
            modified_tokens[first_idx : last_idx + 1] = [merged]
            continue

        # ---- Existing behavior for single-token ph or lang-only overrides ----
        for idx in overlapping_indices:
            token = modified_tokens[idx]

            if "ph" in override.attrs:
                token.meta["ph"] = override.attrs["ph"]
                token.meta["rating"] = 5

            if "lang" in override.attrs:
                token.lang = override.attrs["lang"]

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
