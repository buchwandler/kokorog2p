"""Span-based annotation processing for deterministic override application.

This module provides offset-based span processing for enabling deterministic
phoneme/language override application even with duplicates, punctuation, and
mixed languages.
"""

from collections.abc import Sequence
from itertools import pairwise
from typing import Literal

from kokorog2p.integrations import coerce_override_spans
from kokorog2p.types import TextReplacement, TokenSpan


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
            covered_tokens = modified_tokens[first_idx : last_idx + 1]
            merged_parts = [covered_tokens[0].text]
            for previous, current in pairwise(covered_tokens):
                gap = current.char_start - previous.char_end
                if gap > 0:
                    merged_parts.append(" " * gap)
                merged_parts.append(current.text)
            merged_text = "".join(merged_parts)
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


def apply_text_replacements_to_tokens(
    tokens: list[TokenSpan],
    source: str,
    replacements: Sequence[TextReplacement],
    *,
    default_lang: str | None = None,
) -> tuple[list[TokenSpan], list[str]]:
    """Merge tokens covered by source-aligned semantic replacements.

    Replacement offsets are in ``source`` coordinates.  A replacement is
    applied only when it covers complete token content and all covered tokens
    have the same effective language and no phoneme override.  This keeps
    semantic normalization from silently consuming an annotation boundary.
    """

    warnings: list[str] = []
    modified_tokens = [
        TokenSpan(
            text=token.text,
            char_start=token.char_start,
            char_end=token.char_end,
            lang=token.lang,
            extended_text=token.extended_text,
            meta=dict(token.meta),
        )
        for token in tokens
    ]

    def normalized_lang(lang: str | None) -> str | None:
        if not lang:
            return None
        return lang.lower().replace("_", "-")

    sorted_replacements = sorted(replacements, key=lambda item: (item.start, item.end))
    coalesced_replacements: list[TextReplacement] = []
    index = 0
    while index < len(sorted_replacements):
        replacement = sorted_replacements[index]
        overlapping_indices = [
            token_index
            for token_index, token in enumerate(modified_tokens)
            if token.char_start < replacement.end and token.char_end > replacement.start
        ]
        if len(overlapping_indices) == 1:
            token = modified_tokens[overlapping_indices[0]]
            fragments = [replacement]
            next_index = index + 1
            while next_index < len(sorted_replacements):
                candidate = sorted_replacements[next_index]
                if (
                    candidate.start < token.char_start
                    or candidate.end > token.char_end
                    or candidate.start < fragments[-1].end
                    or any(
                        character.isalnum()
                        for character in source[fragments[-1].end : candidate.start]
                    )
                ):
                    break
                fragments.append(candidate)
                next_index += 1
            if (
                len(fragments) > 1
                and fragments[0].start == token.char_start
                and fragments[-1].end == token.char_end
            ):
                replacement_parts = [fragments[0].text]
                for previous, current in pairwise(fragments):
                    replacement_parts.append(source[previous.end : current.start])
                    replacement_parts.append(current.text)
                coalesced_replacements.append(
                    TextReplacement(
                        start=fragments[0].start,
                        end=fragments[-1].end,
                        text="".join(replacement_parts),
                        kind=fragments[0].kind,
                        priority=max(fragment.priority for fragment in fragments),
                        language=fragments[0].language,
                        stages=fragments[0].stages,
                    )
                )
                index = next_index
                continue
        coalesced_replacements.append(replacement)
        index += 1

    for replacement in coalesced_replacements:
        replacement_start = replacement.start
        replacement_end = replacement.end
        replacement_text = replacement.text

        # Spokenform may include a sentence-final period in a structured
        # replacement (for example ``30C.``).  Keep that period as its own
        # source token when the source tokenizer did so, while retaining the
        # exact semantic replacement for the alphanumeric token.
        if (
            replacement_end > replacement_start
            and replacement_end <= len(source)
            and source[replacement_end - 1] == "."
            and replacement_text.endswith(".")
            and modified_tokens
            and modified_tokens[-1].char_end >= replacement_end
        ):
            candidate_indices = [
                index
                for index, token in enumerate(modified_tokens)
                if token.char_start < replacement_end
                and token.char_end > replacement_start
            ]
            if candidate_indices:
                final_token = modified_tokens[candidate_indices[-1]]
                if final_token.char_end == replacement_end and final_token.text == ".":
                    replacement_end -= 1
                    replacement_text = replacement_text[:-1]

        if replacement_start < 0 or replacement_end > len(source):
            warnings.append(
                f"[REPLACEMENT] {replacement.kind} span "
                f"[{replacement_start}:{replacement_end}] is outside source; skipping"
            )
            continue
        overlapping_indices = [
            index
            for index, token in enumerate(modified_tokens)
            if token.char_start < replacement_end and token.char_end > replacement_start
        ]
        if not overlapping_indices:
            warnings.append(
                f"[REPLACEMENT] {replacement.kind} span "
                f"[{replacement_start}:{replacement_end}] overlaps no tokens; skipping"
            )
            continue

        first_idx = overlapping_indices[0]
        last_idx = overlapping_indices[-1]
        covered = modified_tokens[first_idx : last_idx + 1]
        if any("ph" in token.meta for token in covered):
            warnings.append(
                f"[REPLACEMENT] {replacement.kind} span "
                f"[{replacement_start}:{replacement_end}] crosses a phoneme "
                "override; skipping"
            )
            continue

        effective_languages = {
            normalized_lang(token.lang or default_lang) for token in covered
        }
        if len(effective_languages) > 1:
            warnings.append(
                f"[REPLACEMENT] {replacement.kind} span "
                f"[{replacement_start}:{replacement_end}] crosses language "
                "overrides; skipping"
            )
            continue

        first_token = covered[0]
        last_token = covered[-1]
        if (
            replacement_start < first_token.char_start
            or replacement_end > last_token.char_end
        ):
            warnings.append(
                f"[REPLACEMENT] {replacement.kind} span "
                f"[{replacement_start}:{replacement_end}] does not align to "
                "complete tokens; skipping"
            )
            continue

        merged = TokenSpan(
            text=source[replacement_start:replacement_end],
            char_start=replacement_start,
            char_end=replacement_end,
            lang=first_token.lang,
            extended_text=replacement_text,
            meta=dict(first_token.meta),
        )
        merged.meta["_extended_text_changed"] = True
        merged.meta["_extended_text"] = replacement_text
        merged.meta["_replacement_kind"] = replacement.kind
        merged.meta["_replacement_rule"] = replacement.rule
        merged.meta["_replacement_language"] = replacement.language
        merged.meta["_replacement_stages"] = replacement.stages
        modified_tokens[first_idx : last_idx + 1] = [merged]

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
    "apply_text_replacements_to_tokens",
    "tokens_to_text_with_spacing",
]
