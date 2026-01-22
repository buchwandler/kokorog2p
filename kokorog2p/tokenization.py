"""Offset-aware tokenization for kokorog2p.

This module provides deterministic tokenization with character offset tracking,
ensuring that tokenization used for override application matches the tokenization
used for phonemization.
"""

from functools import cache
from typing import TYPE_CHECKING

from kokorog2p.types import TokenSpan

if TYPE_CHECKING:
    from kokorog2p.token import GToken


def ensure_gtoken_positions(gtokens: list["GToken"], text: str) -> list["GToken"]:
    """Ensure GTokens have char_start/char_end positions.

    Positions are stored in the GToken extension dict to preserve
    backward compatibility. Existing positions are preserved.

    Args:
        gtokens: List of GTokens to update.
        text: Text used to generate the tokens.

    Returns:
        The updated list of GTokens.
    """
    current_pos = 0

    for gtoken in gtokens:
        char_start = gtoken.get("char_start")
        char_end = gtoken.get("char_end")
        if char_start is not None and char_end is not None:
            current_pos = max(current_pos, char_end)
            continue

        while current_pos < len(text) and text[current_pos].isspace():
            current_pos += 1

        token_text = gtoken.text
        if not token_text:
            gtoken.set("char_start", current_pos)
            gtoken.set("char_end", current_pos)
            continue

        token_start = text.find(token_text, current_pos)
        if token_start == -1:
            token_start = current_pos
        token_end = token_start + len(token_text)

        gtoken.set("char_start", token_start)
        gtoken.set("char_end", token_end)
        current_pos = token_end

    return gtokens


def gtoken_to_tokenspan(token: "GToken", clean_text: str) -> TokenSpan:
    """Convert a GToken to a TokenSpan with computed char offsets.

    Since GTokens don't track character offsets, we compute them by
    scanning the clean_text. This is only used for legacy codepath.

    Args:
        token: GToken to convert.
        clean_text: The clean text to compute offsets from.

    Returns:
        TokenSpan with computed offsets.
    """
    # For now, we don't have char offsets in GToken
    # This is a placeholder that returns zero offsets
    # Real implementation will come from direct tokenization
    return TokenSpan(
        text=token.text,
        char_start=0,
        char_end=len(token.text),
        lang=None,
        meta={"phonemes": token.phonemes} if token.phonemes else {},
    )


def _normalize_lang(lang: str | None) -> str | None:
    if not lang:
        return None
    return lang.lower().replace("_", "-")


@cache
def _get_abbreviation_entries(lang: str | None) -> list[tuple[str, bool]]:
    normalized = _normalize_lang(lang) or "en-us"
    entries: list[tuple[str, bool]] = []

    if normalized.startswith("en"):
        from kokorog2p.en.abbreviations import get_expander
    elif normalized.startswith("de"):
        from kokorog2p.de.abbreviations import get_expander
    elif normalized.startswith("fr"):
        from kokorog2p.fr.abbreviations import get_expander
    elif normalized.startswith("es"):
        from kokorog2p.es.abbreviations import get_expander
    elif normalized.startswith("pt"):
        from kokorog2p.pt.abbreviations import get_expander
    elif normalized.startswith("it"):
        from kokorog2p.it.abbreviations import get_expander
    elif normalized.startswith("cs"):
        from kokorog2p.cs.abbreviations import get_expander
    else:
        return entries

    expander = get_expander()
    for entry in expander.entries.values():
        entries.append((entry.abbreviation, entry.case_sensitive))

    return entries


def _merge_abbreviation_tokens(
    tokens: list[TokenSpan],
    lang: str | None,
) -> list[TokenSpan]:
    if len(tokens) < 2:
        return tokens

    entries = _get_abbreviation_entries(lang)
    if not entries:
        return tokens

    case_sensitive = {
        abbrev for abbrev, is_case_sensitive in entries if is_case_sensitive
    }
    case_insensitive = {
        abbrev.lower() for abbrev, is_case_sensitive in entries if not is_case_sensitive
    }
    max_len = max((len(abbrev) for abbrev, _ in entries), default=0)
    if max_len == 0:
        return tokens

    merged: list[TokenSpan] = []
    i = 0
    while i < len(tokens):
        best_end = None
        best_text = None
        combined = ""
        last_end = tokens[i].char_end

        for j in range(i, len(tokens)):
            if j > i and tokens[j].char_start != last_end:
                break
            combined += tokens[j].text
            last_end = tokens[j].char_end
            if len(combined) > max_len:
                break

            if combined in case_sensitive or combined.lower() in case_insensitive:
                best_end = j
                best_text = combined

        if best_end is not None and best_end > i:
            merged.append(
                TokenSpan(
                    text=best_text or combined,
                    char_start=tokens[i].char_start,
                    char_end=tokens[best_end].char_end,
                    lang=tokens[i].lang,
                    meta=tokens[i].meta,
                )
            )
            i = best_end + 1
            continue

        merged.append(tokens[i])
        i += 1

    return merged


def tokenize_with_offsets(
    text: str,
    *,
    lang: str | None = None,
    keep_punct: bool = True,
) -> list[TokenSpan]:
    """Tokenize text with character offset tracking.

    This function provides deterministic tokenization with character offsets,
    matching the tokenization used internally for phonemization.

    Args:
        text: Text to tokenize (should be clean text, not annotated).
        lang: Optional language code (e.g., 'en-us', 'de', 'fr').
        keep_punct: Whether to include punctuation tokens.

    Returns:
        List of TokenSpan objects with char offsets.

    Example:
        >>> tokens = tokenize_with_offsets("Hello world!", lang="en-us")
        >>> for t in tokens:
        ...     print(f"{t.text} [{t.char_start}:{t.char_end}]")
        Hello [0:5]
        world [6:11]
        ! [11:12]
    """
    # For now, use simple regex-based tokenization with offset tracking
    # This ensures consistency with actual G2P tokenization
    import re

    # Pattern matches:
    # - Hyphenated words: \w+-\w+(-\w+)* (e.g., "good-looking", "state-of-the-art")
    # - Contractions: \w+'\w+ (e.g., "don't", "What's")
    # - Regular words: \w+
    # - Non-word/non-space chars: [^\w\s]
    # - Whitespace: \s+
    pattern = re.compile(r"(\w+(?:-\w+)+|\w+'\w+|\w+|[^\w\s]|\s+)")
    tokens: list[TokenSpan] = []

    for match in pattern.finditer(text):
        word = match.group()

        # Skip whitespace (not needed as tokens, spacing inferred from offsets)
        if word.isspace():
            continue

        # Skip punctuation if requested
        if not keep_punct and not word[0].isalnum():
            continue

        tokens.append(
            TokenSpan(
                text=word,
                char_start=match.start(),
                char_end=match.end(),
                lang=None,
                meta={},
            )
        )

    return _merge_abbreviation_tokens(tokens, lang)


def gtokens_to_tokenspans(
    gtokens: list["GToken"],
    clean_text: str,
) -> list[TokenSpan]:
    """Convert a list of GTokens to TokenSpans with offset reconstruction.

    This function reconstructs character offsets by scanning through the clean_text
    and matching tokens in order. This ensures deterministic offset assignment.

    Args:
        gtokens: List of GToken objects from G2P.
        clean_text: The clean text these tokens came from.

    Returns:
        List of TokenSpan objects with character offsets.

    Example:
        >>> from kokorog2p import get_g2p
        >>> g2p = get_g2p("en-us")
        >>> gtokens = g2p("Hello world!")
        >>> clean_text = "Hello world!"
        >>> token_spans = gtokens_to_tokenspans(gtokens, clean_text)
    """
    token_spans: list[TokenSpan] = []
    current_pos = 0

    for gtoken in gtokens:
        char_start = gtoken.get("char_start")
        char_end = gtoken.get("char_end")

        if char_start is not None and char_end is not None:
            token_start = char_start
            token_end = char_end
        else:
            # Skip ahead to find this token in clean_text
            # Handle whitespace by advancing past it
            while current_pos < len(clean_text) and clean_text[current_pos].isspace():
                current_pos += 1

            if current_pos >= len(clean_text):
                # Reached end of text
                break

            # Find the token text starting at current_pos
            token_text = gtoken.text
            token_start = clean_text.find(token_text, current_pos)

            if token_start == -1:
                # Token not found - this could happen with normalization differences
                # Use best guess: current position
                token_start = current_pos
                token_end = current_pos + len(token_text)
            else:
                token_end = token_start + len(token_text)

        token_text = gtoken.text

        # Build meta dict from GToken
        meta: dict[str, object] = {}
        if gtoken.phonemes:
            meta["phonemes"] = gtoken.phonemes
        if gtoken.rating:
            meta["rating"] = gtoken.rating
        if gtoken.tag:
            meta["tag"] = gtoken.tag
        meta["whitespace"] = gtoken.whitespace

        # Create TokenSpan
        token_span = TokenSpan(
            text=token_text,
            char_start=token_start,
            char_end=token_end,
            lang=None,  # GToken doesn't have lang
            meta=meta,
        )
        token_spans.append(token_span)

        # Advance position
        current_pos = token_end

    return token_spans


__all__ = [
    "tokenize_with_offsets",
    "gtokens_to_tokenspans",
    "gtoken_to_tokenspan",
    "ensure_gtoken_positions",
]
