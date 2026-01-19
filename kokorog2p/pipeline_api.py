"""Pipeline-friendly phonemization API for kokorog2p.

This module provides the new span-based phonemization API that pykokoro should use.
It supports deterministic override application, per-span language switching, and
direct token ID output.
"""

from typing import TYPE_CHECKING, Literal

from kokorog2p.span_processing import apply_overrides_to_tokens, parse_ssmd_to_spans
from kokorog2p.tokenization import gtokens_to_tokenspans, tokenize_with_offsets
from kokorog2p.types import OverrideSpan, PhonemizeResult, TokenSpan
from kokorog2p.vocab import phonemes_to_ids

if TYPE_CHECKING:
    from kokorog2p.base import G2PBase


def phonemize_to_result(
    clean_text: str,
    *,
    lang: str | None = None,
    overrides: list[OverrideSpan] | None = None,
    return_ids: bool = True,
    return_phonemes: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    g2p: "G2PBase | None" = None,
) -> PhonemizeResult:
    """Phonemize text with span-based override application.

    This is the primary API for pipeline-friendly phonemization. It supports:
    - Deterministic override application using character offsets
    - Per-span language switching
    - Direct token ID output
    - Full traceability with warnings

    Args:
        clean_text: Clean text (no markup) to phonemize.
        lang: Language code (e.g., 'en-us', 'de', 'fr'). Default: 'en-us'.
        overrides: Optional list of OverrideSpan to apply.
        return_ids: Whether to return token IDs in result.
        return_phonemes: Whether to return phoneme string in result.
        alignment: Override alignment mode:
            - "span": Use offset-based alignment (deterministic, default)
            - "legacy": Use old word-based alignment (backward compat)
        g2p: Optional G2P instance to reuse (for performance).

    Returns:
        PhonemizeResult with clean_text, tokens, phonemes, token_ids, and warnings.

    Example:
        >>> # Simple phonemization
        >>> result = phonemize_to_result("Hello world!")
        >>> result.phonemes
        'hɛloʊ wɝld!'
        >>> result.token_ids
        [...]

        >>> # With overrides
        >>> from kokorog2p.types import OverrideSpan
        >>> overrides = [OverrideSpan(0, 5, {"ph": "hɛˈloʊ"})]
        >>> result = phonemize_to_result("Hello world!", overrides=overrides)
        >>> result.phonemes
        'hɛˈloʊ wɝld!'

        >>> # With language override
        >>> overrides = [OverrideSpan(6, 11, {"lang": "de"})]
        >>> result = phonemize_to_result("Hello Welt!", overrides=overrides)
    """
    from kokorog2p import get_g2p

    lang = lang or "en-us"
    warnings: list[str] = []

    # Get or create G2P instance
    if g2p is None:
        g2p = get_g2p(lang, markdown_syntax="disabled")

    # Tokenize clean text with offset tracking
    if alignment == "span":
        # Use new span-based alignment
        token_spans = tokenize_with_offsets(clean_text, lang=lang, keep_punct=True)
    else:
        # Legacy: use G2P's tokenization and reconstruct offsets
        gtokens = g2p(clean_text)
        token_spans = gtokens_to_tokenspans(gtokens, clean_text)

    # Apply overrides if provided
    if overrides:
        token_spans, override_warnings = apply_overrides_to_tokens(
            token_spans, overrides, mode="snap"
        )
        warnings.extend(override_warnings)

    # Phonemize tokens based on language and overrides
    phonemized_tokens, phonemize_warnings = _phonemize_token_spans(
        token_spans, g2p, lang
    )
    warnings.extend(phonemize_warnings)

    # Build phoneme string if requested
    phonemes: str | None = None
    if return_phonemes:
        phonemes = _build_phoneme_string(phonemized_tokens)

    # Build token IDs if requested
    token_ids: list[int] | None = None
    if return_ids and phonemes is not None:
        try:
            token_ids = phonemes_to_ids(phonemes)
        except Exception as e:
            warnings.append(f"Failed to convert phonemes to IDs: {e}")
            token_ids = None

    return PhonemizeResult(
        clean_text=clean_text,
        tokens=phonemized_tokens,
        phonemes=phonemes,
        token_ids=token_ids,
        warnings=warnings,
    )


def _phonemize_token_spans(
    token_spans: list[TokenSpan],
    g2p: "G2PBase",
    default_lang: str,
) -> tuple[list[TokenSpan], list[str]]:
    """Phonemize token spans, handling per-span language switching.

    Args:
        token_spans: List of token spans to phonemize.
        g2p: G2P instance for default language.
        default_lang: Default language code.

    Returns:
        Tuple of (phonemized_tokens, warnings).
    """
    from kokorog2p import get_g2p

    warnings: list[str] = []
    phonemized_tokens: list[TokenSpan] = []
    g2p_cache: dict[str, G2PBase] = {default_lang: g2p}

    for token in token_spans:
        # Determine language for this token
        token_lang = token.lang or default_lang

        # Get G2P instance for this language
        if token_lang not in g2p_cache:
            try:
                g2p_cache[token_lang] = get_g2p(token_lang, markdown_syntax="disabled")
            except Exception as e:
                warnings.append(
                    f"Failed to load G2P for language '{token_lang}' "
                    f"(token '{token.text}'): {e}"
                )
                # Fall back to default language
                token_lang = default_lang

        token_g2p = g2p_cache[token_lang]

        # Check if phoneme override is present
        if "ph" in token.meta:
            # Use override phonemes
            phonemes = str(token.meta["ph"])
        else:
            # Phonemize using G2P
            try:
                gtokens = token_g2p(token.text)
                if gtokens and gtokens[0].phonemes:
                    phonemes = gtokens[0].phonemes
                else:
                    phonemes = ""
                    if token.text.strip() and not _is_punctuation(token.text):
                        warnings.append(
                            f"No phonemes generated for token '{token.text}' "
                            f"at position {token.char_start}"
                        )
            except Exception as e:
                warnings.append(
                    f"Phonemization failed for token '{token.text}' "
                    f"at position {token.char_start}: {e}"
                )
                phonemes = ""

        # Create phonemized token
        phonemized_token = TokenSpan(
            text=token.text,
            char_start=token.char_start,
            char_end=token.char_end,
            lang=token.lang,
            meta={**token.meta, "phonemes": phonemes},
        )
        phonemized_tokens.append(phonemized_token)

    return phonemized_tokens, warnings


def _build_phoneme_string(tokens: list[TokenSpan]) -> str:
    """Build a space-separated phoneme string from tokens.

    Args:
        tokens: List of phonemized token spans.

    Returns:
        Phoneme string with appropriate spacing.
    """
    parts: list[str] = []

    for i, token in enumerate(tokens):
        phonemes = token.meta.get("phonemes", "")
        if not phonemes:
            # No phonemes - might be punctuation or failed phonemization
            # Check if it's punctuation and include as-is
            if _is_punctuation(token.text):
                parts.append(token.text)
            continue

        parts.append(str(phonemes))

        # Add space if needed before next token
        if i + 1 < len(tokens):
            next_token = tokens[i + 1]
            # Add space unless next token is punctuation
            if not _is_punctuation(next_token.text):
                gap = next_token.char_start - token.char_end
                if gap > 0:
                    parts.append(" ")

    return "".join(parts).strip()


def _is_punctuation(text: str) -> bool:
    """Check if text is punctuation.

    Args:
        text: Text to check.

    Returns:
        True if text is punctuation.
    """
    if not text:
        return False
    # Common punctuation characters
    punct = {
        ",",
        ".",
        "!",
        "?",
        ";",
        ":",
        "-",
        "—",
        "...",
        "…",
        "(",
        ")",
        "[",
        "]",
        "{",
        "}",
    }
    return text.strip() in punct or all(not c.isalnum() for c in text)


# ============================================================================
# Convenience wrappers for SSMD/SpeechMarkdown
# ============================================================================


def phonemize_ssmd_to_result(
    text: str,
    *,
    lang: str | None = None,
    return_ids: bool = True,
    return_phonemes: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    g2p: "G2PBase | None" = None,
) -> PhonemizeResult:
    """Phonemize SSMD-annotated text using span-based processing.

    This is a convenience wrapper that parses SSMD annotations and calls
    phonemize_to_result.

    Args:
        text: Text with SSMD annotations (e.g., "[Hello]{ph='hɛloʊ'}").
        lang: Language code (default: 'en-us').
        return_ids: Whether to return token IDs.
        return_phonemes: Whether to return phoneme string.
        alignment: Override alignment mode ('span' or 'legacy').
        g2p: Optional G2P instance to reuse.

    Returns:
        PhonemizeResult with clean_text, tokens, phonemes, token_ids, and warnings.

    Example:
        >>> result = phonemize_ssmd_to_result('[Hello]{ph="hɛloʊ"} world!')
        >>> result.phonemes
        'hɛloʊ wɝld!'
    """
    # Parse SSMD to clean text and overrides
    clean_text, overrides, parse_warnings = parse_ssmd_to_spans(text)

    # Phonemize with overrides
    result = phonemize_to_result(
        clean_text,
        lang=lang,
        overrides=overrides,
        return_ids=return_ids,
        return_phonemes=return_phonemes,
        alignment=alignment,
        g2p=g2p,
    )

    # Prepend parse warnings
    result.warnings = parse_warnings + result.warnings

    return result


def phonemize_ssmd(
    text: str,
    *,
    lang: str | None = None,
    alignment: Literal["span", "legacy"] = "span",
    g2p: "G2PBase | None" = None,
) -> str:
    """Phonemize SSMD-annotated text and return phoneme string.

    This is a simple convenience wrapper for phonemize_ssmd_to_result
    that returns only the phoneme string.

    Args:
        text: Text with SSMD annotations.
        lang: Language code (default: 'en-us').
        alignment: Override alignment mode ('span' or 'legacy').
        g2p: Optional G2P instance to reuse.

    Returns:
        Phoneme string.

    Example:
        >>> phonemize_ssmd('[Hello]{ph="hɛloʊ"} world!')
        'hɛloʊ wɝld!'
    """
    result = phonemize_ssmd_to_result(
        text,
        lang=lang,
        return_ids=False,
        return_phonemes=True,
        alignment=alignment,
        g2p=g2p,
    )
    return result.phonemes or ""


__all__ = [
    "phonemize_to_result",
    "phonemize_ssmd",
    "phonemize_ssmd_to_result",
]
