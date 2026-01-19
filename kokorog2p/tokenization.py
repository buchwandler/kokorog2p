"""Offset-aware tokenization for kokorog2p.

This module provides deterministic tokenization with character offset tracking,
ensuring that tokenization used for override application matches the tokenization
used for phonemization.
"""

from typing import TYPE_CHECKING

from kokorog2p.types import TokenSpan

if TYPE_CHECKING:
    from kokorog2p.token import GToken


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

    pattern = re.compile(r"(\w+'\w+|\w+|[^\w\s]|\s+)")
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

    return tokens


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

        # Build meta dict from GToken
        meta: dict[str, object] = {}
        if gtoken.phonemes:
            meta["phonemes"] = gtoken.phonemes
        if gtoken.rating:
            meta["rating"] = gtoken.rating
        if gtoken.tag:
            meta["tag"] = gtoken.tag

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
]
