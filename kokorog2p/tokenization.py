"""Offset-aware tokenization for kokorog2p.

This module provides deterministic tokenization with character offset tracking,
ensuring that tokenization used for override application matches the tokenization
used for phonemization.
"""

from typing import TYPE_CHECKING, Any

from kokorog2p.types import TokenAnnotation, TokenAnnotationLike, TokenSpan

if TYPE_CHECKING:
    from kokorog2p.token import GToken


COMMON_COMBINING_MARK_RANGES = r"\u0300-\u036f"
ARABIC_COMBINING_MARK_RANGES = r"\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed"
WORD_MARK_RANGES = COMMON_COMBINING_MARK_RANGES + ARABIC_COMBINING_MARK_RANGES


def _annotation_value(annotation: object, name: str, default: object = None) -> object:
    value = getattr(annotation, name, default)
    if name == "language" and value is None:
        value = getattr(annotation, "lang", default)
    return value


def coerce_token_annotations(
    text: str,
    annotations: list[TokenAnnotationLike] | tuple[TokenAnnotationLike, ...] | Any,
) -> list[TokenAnnotation]:
    """Validate compatible external token annotations in source coordinates."""
    if annotations is None:
        return []
    result: list[TokenAnnotation] = []
    previous_end = 0
    for index, raw in enumerate(annotations):
        start = _annotation_value(raw, "start")
        end = _annotation_value(raw, "end")
        if isinstance(start, bool) or not isinstance(start, int):
            raise TypeError(f"annotation {index} start must be an integer")
        if isinstance(end, bool) or not isinstance(end, int):
            raise TypeError(f"annotation {index} end must be an integer")
        if not (0 <= start < end <= len(text)) or start < previous_end:
            raise ValueError(f"annotation {index} has invalid or overlapping bounds")
        raw_text = _annotation_value(raw, "text")
        if raw_text is not None and (
            not isinstance(raw_text, str) or raw_text != text[start:end]
        ):
            raise ValueError(f"annotation {index} text does not match source slice")
        values: dict[str, str | None] = {}
        for name in ("pos", "tag", "lemma", "language"):
            value = _annotation_value(raw, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"annotation {index} {name} must be a string or None")
            values[name] = value or None
        result.append(TokenAnnotation(start, end, raw_text, **values))
        previous_end = end
    return result


def tokens_from_annotations(
    text: str,
    annotations: list[TokenAnnotationLike] | tuple[TokenAnnotationLike, ...] | Any,
    *,
    lang: str | None = None,
    keep_punct: bool = True,
) -> list[TokenSpan]:
    """Tokenize text and attach validated external linguistic metadata."""
    validated = coerce_token_annotations(text, annotations)
    tokens = tokenize_with_offsets(text, lang=lang, keep_punct=keep_punct)
    for token in tokens:
        for annotation in validated:
            if annotation.end <= token.char_start:
                continue
            if annotation.start >= token.char_end:
                break
            if (
                annotation.start <= token.char_start
                and token.char_end <= annotation.end
            ):
                token.meta.update(
                    {
                        key: value
                        for key, value in {
                            "pos": annotation.pos,
                            "tag": annotation.tag,
                            "lemma": annotation.lemma,
                        }.items()
                        if value is not None
                    }
                )
                token.lang = annotation.language or lang
                break
    return tokens


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
    if token.get("drop"):
        meta["drop"] = True
    source_kind = token.get("source_kind")
    if source_kind:
        meta["source_kind"] = source_kind
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

    # Numeric alternatives must precede regular words and punctuation so
    # structured forms reach number conversion intact.
    number = r"(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)+"
    leading_decimal = r"(?<![\w.])\.\d+"
    grouped_integer = r"\d{1,3}(?:,\d{3})+"
    word_chars = r"\w" + WORD_MARK_RANGES
    pattern = re.compile(
        rf"({number}|{leading_decimal}|{grouped_integer}|"
        rf"[{word_chars}]+(?:-[{word_chars}]+)+|"
        rf"[{word_chars}]+(?:['\u2019][{word_chars}]+)+|"
        rf"[{word_chars}]+|\.{{2,}}|…|[^\w\s{WORD_MARK_RANGES}]|\s+)"
    )
    tokens: list[TokenSpan] = []

    for match in pattern.finditer(text):
        word = match.group()

        # Skip whitespace (not needed as tokens, spacing inferred from offsets)
        if word.isspace():
            continue

        # Skip punctuation if requested
        if not keep_punct and not any(char.isalnum() for char in word):
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
    "ensure_gtoken_positions",
    "gtoken_to_tokenspan",
    "gtokens_to_tokenspans",
    "tokenize_with_offsets",
]
