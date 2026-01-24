"""Offset-aware tokenization for kokorog2p.

This module provides deterministic tokenization with character offset tracking,
ensuring that tokenization used for override application matches the tokenization
used for phonemization.
"""

from typing import TYPE_CHECKING

from kokorog2p.abbreviation_utils import merge_abbreviation_tokens
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

        token_start, token_end, current_pos = _infer_token_offsets(
            gtoken.text, text, current_pos
        )
        gtoken.set("char_start", token_start)
        gtoken.set("char_end", token_end)

    return gtokens


def gtoken_to_tokenspan(
    token: "GToken",
    clean_text: str,
    *,
    current_pos: int = 0,
) -> TokenSpan:
    """Convert a GToken to a TokenSpan with computed char offsets.

    Since GTokens don't track character offsets, we compute them by
    scanning the clean_text using the same matching rules as
    gtokens_to_tokenspans.

    Args:
        token: GToken to convert.
        clean_text: The clean text to compute offsets from.
        current_pos: Starting position for token matching.

    Returns:
        TokenSpan with computed offsets.
    """
    token_start, token_end, _ = _resolve_gtoken_offsets(token, clean_text, current_pos)
    return TokenSpan(
        text=token.text,
        char_start=token_start,
        char_end=token_end,
        lang=None,
        extended_text=None,
        meta=_build_gtoken_meta(token),
    )


def _merge_abbreviation_tokens(
    tokens: list[TokenSpan],
    lang: str | None,
) -> list[TokenSpan]:
    def is_break(prev: TokenSpan, current: TokenSpan, last_end: int) -> bool:
        return current.char_start != last_end

    def build_token(start: TokenSpan, end: TokenSpan, text: str) -> TokenSpan:
        return TokenSpan(
            text=text,
            char_start=start.char_start,
            char_end=end.char_end,
            lang=start.lang,
            extended_text=start.extended_text,
            meta=start.meta,
        )

    return merge_abbreviation_tokens(
        tokens,
        lang,
        is_break=is_break,
        build_token=build_token,
    )


def _infer_token_offsets(
    token_text: str,
    clean_text: str,
    current_pos: int,
) -> tuple[int, int, int]:
    pos = current_pos
    while pos < len(clean_text) and clean_text[pos].isspace():
        pos += 1

    if not token_text:
        return pos, pos, pos

    token_start = clean_text.find(token_text, pos)
    if token_start == -1:
        token_start = pos
    token_end = token_start + len(token_text)
    return token_start, token_end, token_end


def _build_gtoken_meta(token: "GToken") -> dict[str, object]:
    meta: dict[str, object] = {}
    if token.phonemes:
        meta["phonemes"] = token.phonemes
    if token.rating:
        meta["rating"] = token.rating
    if token.tag:
        meta["tag"] = token.tag
    meta["whitespace"] = token.whitespace
    return meta


def _resolve_gtoken_offsets(
    token: "GToken",
    clean_text: str,
    current_pos: int,
) -> tuple[int, int, int]:
    char_start = token.get("char_start")
    char_end = token.get("char_end")
    if char_start is not None and char_end is not None:
        return char_start, char_end, max(current_pos, char_end)

    token_start, token_end, next_pos = _infer_token_offsets(
        token.text, clean_text, current_pos
    )
    return token_start, token_end, next_pos


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
    # - Contractions: \w+(?:'\w+)+ (e.g., "don't", "What's", "I'd've")
    # - Regular words: \w+
    # - Non-word/non-space chars: [^\w\s]
    # - Whitespace: \s+
    pattern = re.compile(r"(\w+(?:-\w+)+|\w+(?:'\w+)+|\w+|[^\w\s]|\s+)")
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
                extended_text=None,
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
        token_start, token_end, current_pos = _resolve_gtoken_offsets(
            gtoken, clean_text, current_pos
        )
        token_span = TokenSpan(
            text=gtoken.text,
            char_start=token_start,
            char_end=token_end,
            lang=None,
            extended_text=None,
            meta=_build_gtoken_meta(gtoken),
        )
        token_spans.append(token_span)

    return token_spans


__all__ = [
    "tokenize_with_offsets",
    "gtokens_to_tokenspans",
    "gtoken_to_tokenspan",
    "ensure_gtoken_positions",
]
