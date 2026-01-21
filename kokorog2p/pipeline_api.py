"""Pipeline-friendly phonemization API for kokorog2p.

This module provides the new span-based phonemization API that pykokoro should use.
It supports deterministic override application, per-span language switching, and
direct token ID output.
"""

from typing import TYPE_CHECKING, Literal

from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.span_processing import apply_overrides_to_tokens
from kokorog2p.tokenization import gtokens_to_tokenspans, tokenize_with_offsets
from kokorog2p.types import OverrideSpan, PhonemizeResult, TokenSpan
from kokorog2p.vocab import filter_for_kokoro, phonemes_to_ids, validate_for_kokoro

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
    overlap: Literal["snap", "strict"] = "snap",
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
        overlap: Overlap handling mode for applying overrides:
            - "snap": Apply to intersecting tokens, emit warning on
              partial boundary overlap (default)
            - "strict": Skip partial boundary overlap, emit warning
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

    # Normalize punctuation into Kokoro-compatible forms early
    # (e.g. '-' -> '—', '...' -> '…', fullwidth punctuation -> ASCII)
    clean_text = normalize_punctuation(clean_text)

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
            token_spans, overrides, mode=overlap
        )
        warnings.extend(override_warnings)

    # Phonemize tokens based on language and overrides
    phonemized_tokens, phonemize_warnings = _phonemize_token_spans(
        token_spans, g2p, lang
    )
    warnings.extend(phonemize_warnings)

    # Build phoneme string if needed for output OR for IDs
    phoneme_str: str | None = None
    if return_phonemes or return_ids:
        phoneme_str = _build_phoneme_string(phonemized_tokens)

    phonemes: str | None = phoneme_str if return_phonemes else None

    # Build token IDs if requested (independent of return_phonemes)
    token_ids: list[int] | None = None
    if return_ids and phoneme_str is not None:
        is_valid, invalid = validate_for_kokoro(phoneme_str)
        if not is_valid:
            warnings.append(
                "Phoneme string contains chars not in Kokoro vocab; "
                "they will be dropped: " + "".join(sorted(set(invalid)))
            )
            phoneme_str = filter_for_kokoro(phoneme_str, replacement="")
        try:
            token_ids = phonemes_to_ids(phoneme_str)
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
                if gtokens:
                    # Concatenate phonemes from all returned tokens
                    # (e.g., "What's" -> ["What", "'s"] -> "wˌʌt" + "s")
                    phoneme_parts = [gt.phonemes for gt in gtokens if gt.phonemes]
                    if phoneme_parts:
                        phonemes = " ".join(phoneme_parts)
                    else:
                        phonemes = ""
                        if token.text.strip() and not _is_punctuation(token.text):
                            warnings.append(
                                f"No phonemes generated for token '{token.text}' "
                                f"at position {token.char_start}"
                            )
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


__all__ = [
    "phonemize_to_result",
]
