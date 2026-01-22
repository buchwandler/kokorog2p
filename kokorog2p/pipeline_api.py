"""Pipeline-friendly phonemization API for kokorog2p.

This module provides the new span-based phonemization API that pykokoro should use.
It supports deterministic override application, per-span language switching, and
direct token ID output.
"""

from collections.abc import Callable
from functools import cache
from typing import TYPE_CHECKING, Any, Literal

from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.span_processing import apply_overrides_to_tokens
from kokorog2p.tokenization import (
    ensure_gtoken_positions,
    gtokens_to_tokenspans,
    tokenize_with_offsets,
)
from kokorog2p.types import OverrideSpan, PhonemizeResult, TokenSpan
from kokorog2p.vocab import filter_for_kokoro, phonemes_to_ids, validate_for_kokoro

if TYPE_CHECKING:
    from kokorog2p.base import G2PBase
    from kokorog2p.token import GToken


def _normalize_lang(lang: str | None) -> str | None:
    if not lang:
        return None
    return lang.lower().replace("_", "-")


@cache
def _get_abbreviation_expander(lang: str | None):
    normalized = _normalize_lang(lang)
    if not normalized:
        normalized = "en-us"

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
        return None

    return get_expander()


def _expand_abbreviation(
    token_text: str,
    before: str,
    after: str,
    lang: str | None,
) -> str | None:
    expander = _get_abbreviation_expander(lang)
    if not expander:
        return None

    entry = expander.get_abbreviation(token_text, case_sensitive=True)
    if entry is None:
        entry = expander.get_abbreviation(token_text, case_sensitive=False)
    if entry is None:
        return None

    if expander.context_detector:
        context = expander.context_detector.detect_context(token_text, before, after)
        return entry.get_expansion(context)

    return entry.expansion


_NUM2WORDS_LANGS: dict[str, list[str]] = {
    "en": ["en"],
    "en-us": ["en"],
    "en-gb": ["en"],
    "de": ["de"],
    "fr": ["fr"],
    "es": ["es"],
    "pt": ["pt"],
    "it": ["it"],
    "cs": ["cs", "cz"],
}


@cache
def _get_language_normalizer(lang: str | None) -> Any | None:
    normalized = _normalize_lang(lang)
    if not normalized:
        normalized = "en-us"

    if normalized.startswith("en"):
        from kokorog2p.en.normalizer import EnglishNormalizer

        return EnglishNormalizer(track_changes=False, expand_abbreviations=True)
    if normalized.startswith("de"):
        from kokorog2p.de.normalizer import GermanNormalizer

        return GermanNormalizer(track_changes=False, expand_abbreviations=True)
    if normalized.startswith("fr"):
        from kokorog2p.fr.normalizer import FrenchNormalizer

        return FrenchNormalizer(track_changes=False, expand_abbreviations=True)
    if normalized.startswith("es"):
        from kokorog2p.es.normalizer import SpanishNormalizer

        return SpanishNormalizer(track_changes=False, expand_abbreviations=True)
    if normalized.startswith("pt"):
        from kokorog2p.pt.normalizer import PortugueseNormalizer

        dialect = "pt" if normalized.startswith("pt-pt") else "br"
        return PortugueseNormalizer(
            track_changes=False,
            expand_abbreviations=True,
            dialect=dialect,
        )
    if normalized.startswith("it"):
        from kokorog2p.it.normalizer import ItalianNormalizer

        return ItalianNormalizer(track_changes=False, expand_abbreviations=True)
    if normalized.startswith("cs"):
        from kokorog2p.cs.normalizer import CzechNormalizer

        return CzechNormalizer(track_changes=False, expand_abbreviations=True)

    return None


@cache
def _get_num2words() -> Callable[..., str] | None:
    try:
        from num2words import num2words

        return num2words
    except ImportError:
        return None


def _expand_number(token_text: str, lang: str | None) -> str | None:
    if not token_text or not token_text.isdigit():
        return None

    normalized = _normalize_lang(lang)
    if normalized is None:
        normalized = "en-us"

    if normalized.startswith("de"):
        try:
            from kokorog2p.de.numbers import GermanNumberConverter

            converter = GermanNumberConverter()
            expanded = converter.convert_cardinal(token_text)
            if expanded and expanded != token_text:
                return expanded.replace("-", " ")
        except Exception:
            return None

    num2words_fn = _get_num2words()
    if not num2words_fn:
        return None

    base_lang = normalized.split("-")[0]
    lang_codes = _NUM2WORDS_LANGS.get(normalized) or _NUM2WORDS_LANGS.get(base_lang)
    if not lang_codes:
        return None

    value = int(token_text)
    for lang_code in lang_codes:
        try:
            expanded = num2words_fn(value, lang=lang_code)
        except (NotImplementedError, ValueError):
            continue
        except Exception:
            return None

        if expanded:
            return expanded.replace("-", " ")

    return None


def _apply_extended_text(
    tokens: list[TokenSpan],
    clean_text: str,
    default_lang: str,
    *,
    use_normalizer_rules: bool = True,
) -> str:
    if not tokens:
        return clean_text

    prefix = clean_text[: tokens[0].char_start]
    parts = [prefix]
    extended_pos = len(prefix)

    for index, token in enumerate(tokens):
        token_lang = token.lang or default_lang
        expanded = None
        used_normalizer = False
        if "ph" not in token.meta:
            before = clean_text[: token.char_start].strip()
            after = clean_text[token.char_end :].strip()
            if use_normalizer_rules:
                normalizer = _get_language_normalizer(token_lang)
                if normalizer and hasattr(normalizer, "normalize_token"):
                    expanded = normalizer.normalize_token(
                        token.text,
                        before=before,
                        after=after,
                    )
                    used_normalizer = True
                    if expanded == token.text:
                        expanded = None

            if expanded is None and not used_normalizer:
                expanded = _expand_abbreviation(token.text, before, after, token_lang)

            if expanded is None:
                expanded = _expand_number(token.text, token_lang)

        if expanded and expanded != token.text:
            token.extended_text = expanded
        else:
            token.extended_text = None

        token_text = token.extended_text or token.text
        token.meta["_extended_char_start"] = extended_pos
        token.meta["_extended_char_end"] = extended_pos + len(token_text)

        parts.append(token_text)
        extended_pos += len(token_text)

        next_start = (
            tokens[index + 1].char_start if index + 1 < len(tokens) else len(clean_text)
        )
        gap = clean_text[token.char_end : next_start]
        parts.append(gap)
        extended_pos += len(gap)

    return "".join(parts)


def _call_g2p_without_abbreviations(g2p: "G2PBase", text: str) -> list["GToken"]:
    original_expand = None
    normalizer_states: list[tuple[object, bool | None, object | None]] = []
    g2p_any: Any = g2p

    if hasattr(g2p_any, "expand_abbreviations"):
        original_expand = g2p_any.expand_abbreviations
        g2p_any.expand_abbreviations = False

    normalizer: Any = getattr(g2p_any, "_normalizer", None)
    if normalizer is None and hasattr(g2p_any, "normalizer"):
        try:
            normalizer = g2p_any.normalizer
        except Exception:
            normalizer = None

    if normalizer is not None and hasattr(normalizer, "expand_abbreviations"):
        original_abbrev = getattr(normalizer, "abbrev_expander", None)
        normalizer_states.append(
            (normalizer, normalizer.expand_abbreviations, original_abbrev)
        )
        normalizer.expand_abbreviations = False
        if hasattr(normalizer, "abbrev_expander"):
            normalizer.abbrev_expander = None

    try:
        return g2p_any(text)
    finally:
        if original_expand is not None:
            g2p_any.expand_abbreviations = original_expand
        for normalizer_obj, expand_value, abbrev_expander in normalizer_states:
            normalizer_any: Any = normalizer_obj
            if expand_value is not None:
                normalizer_any.expand_abbreviations = expand_value
            if hasattr(normalizer_any, "abbrev_expander"):
                normalizer_any.abbrev_expander = abbrev_expander


def phonemize_to_result(
    clean_text: str,
    *,
    lang: str | None = None,
    overrides: list[OverrideSpan] | None = None,
    return_ids: bool = True,
    return_phonemes: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    overlap: Literal["snap", "strict"] = "snap",
    use_normalizer_rules: bool = True,
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
        use_normalizer_rules: Whether to use language normalizer rules when
            building extended_text for span alignment.
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

    g2p_token_spans: list[TokenSpan]
    extended_text: str | None = None

    if alignment == "span":
        # Use new span-based alignment
        token_spans = tokenize_with_offsets(clean_text, lang=lang, keep_punct=True)

        if overrides:
            token_spans, override_warnings = apply_overrides_to_tokens(
                token_spans, overrides, mode=overlap
            )
            warnings.extend(override_warnings)

        extended_text = _apply_extended_text(
            token_spans,
            clean_text,
            lang,
            use_normalizer_rules=use_normalizer_rules,
        )
        gtokens = _call_g2p_without_abbreviations(g2p, extended_text)
        ensure_gtoken_positions(gtokens, extended_text)
        g2p_token_spans = gtokens_to_tokenspans(gtokens, extended_text)
    else:
        # Legacy: use G2P's tokenization and offsets
        gtokens = g2p(clean_text)
        ensure_gtoken_positions(gtokens, clean_text)
        g2p_token_spans = gtokens_to_tokenspans(gtokens, clean_text)
        token_spans = g2p_token_spans

        if overrides:
            token_spans, override_warnings = apply_overrides_to_tokens(
                token_spans, overrides, mode=overlap
            )
            warnings.extend(override_warnings)

    # Phonemize tokens based on language and overrides
    phonemized_tokens, phonemize_warnings = _phonemize_token_spans(
        token_spans, g2p_token_spans, g2p, lang
    )
    warnings.extend(phonemize_warnings)

    # Build phoneme string if needed for output OR for IDs
    phoneme_str: str | None = None
    if return_phonemes or return_ids:
        phoneme_str = _build_phoneme_string(phonemized_tokens, clean_text)

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
        extended_text=extended_text,
        phonemes=phonemes,
        token_ids=token_ids,
        warnings=warnings,
    )


def _phonemize_token_spans(  # noqa: C901
    token_spans: list[TokenSpan],
    g2p_token_spans: list[TokenSpan],
    g2p: "G2PBase",
    default_lang: str,
) -> tuple[list[TokenSpan], list[str]]:
    """Phonemize token spans, handling per-span language switching.

    Args:
        token_spans: List of token spans to phonemize.
        g2p_token_spans: Token spans derived from whole-text G2P.
        g2p: G2P instance for default language.
        default_lang: Default language code.

    Returns:
        Tuple of (phonemized_tokens, warnings).
    """
    from kokorog2p import get_g2p

    warnings: list[str] = []
    phonemized_tokens: list[TokenSpan] = []
    g2p_cache: dict[str, G2PBase] = {default_lang: g2p}
    g2p_index = 0

    for token in token_spans:
        # Determine language for this token
        token_lang = token.lang or default_lang
        token_start = token.meta.get("_extended_char_start", token.char_start)
        token_end = token.meta.get("_extended_char_end", token.char_end)
        use_overlap_mapping = token_lang == default_lang and "ph" not in token.meta
        mapped_parts: list[str] = []

        while (
            g2p_index < len(g2p_token_spans)
            and g2p_token_spans[g2p_index].char_end <= token_start
        ):
            g2p_index += 1

        scan_index = g2p_index
        overlap_spans: list[TokenSpan] = []
        mapped_whitespace: str | None = None
        mapped_tag: str | None = None
        while (
            scan_index < len(g2p_token_spans)
            and g2p_token_spans[scan_index].char_start < token_end
        ):
            overlap_span = g2p_token_spans[scan_index]
            overlap_spans.append(overlap_span)
            whitespace = overlap_span.meta.get("whitespace")
            if whitespace is not None:
                if overlap_span.char_end == token_end:
                    mapped_whitespace = str(whitespace)
            if mapped_tag is None:
                tag = overlap_span.meta.get("tag")
                if tag:
                    mapped_tag = str(tag)
            scan_index += 1

        g2p_index = scan_index

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
        elif token_lang != default_lang:
            # Re-phonemize using language-specific G2P
            try:
                token_text = token.extended_text or token.text
                gtokens = token_g2p(token_text)
                phoneme_parts: list[str] = []
                for gt in gtokens:
                    if gt.phonemes:
                        phoneme_parts.append(gt.phonemes)
                        if gt.whitespace:
                            phoneme_parts.append(gt.whitespace)
                if phoneme_parts:
                    phonemes = "".join(phoneme_parts).strip()
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
        else:
            # Map phonemes from whole-text G2P output
            for overlap_span in overlap_spans:
                g2p_phonemes = overlap_span.meta.get("phonemes", "")
                if g2p_phonemes:
                    mapped_parts.append(str(g2p_phonemes))
                whitespace = overlap_span.meta.get("whitespace")
                if (
                    use_overlap_mapping
                    and whitespace
                    and overlap_span.char_end < token_end
                ):
                    mapped_parts.append(str(whitespace))

            phonemes = "".join(mapped_parts)
            if not phonemes and token.text.strip() and not _is_punctuation(token.text):
                warnings.append(
                    f"No phonemes generated for token '{token.text}' "
                    f"at position {token.char_start}"
                )

        # Create phonemized token
        meta = {**token.meta, "phonemes": phonemes, "whitespace": mapped_whitespace}
        meta.pop("_extended_char_start", None)
        meta.pop("_extended_char_end", None)
        if mapped_tag and "tag" not in meta:
            meta["tag"] = mapped_tag

        phonemized_token = TokenSpan(
            text=token.text,
            char_start=token.char_start,
            char_end=token.char_end,
            lang=token.lang,
            extended_text=token.extended_text,
            meta=meta,
        )
        phonemized_tokens.append(phonemized_token)

    return phonemized_tokens, warnings


def _build_phoneme_string(tokens: list[TokenSpan], clean_text: str) -> str:
    """Build a space-separated phoneme string from tokens.

    Args:
        tokens: List of phonemized token spans.
        clean_text: Original clean text for spacing reconstruction.

    Returns:
        Phoneme string with appropriate spacing.
    """
    parts: list[str] = []

    for i, token in enumerate(tokens):
        phonemes = token.meta.get("phonemes", "")
        whitespace = token.meta.get("whitespace")

        if not phonemes:
            # No phonemes - might be punctuation or failed phonemization
            # Check if it's punctuation and include as-is
            if _is_punctuation_token(token):
                parts.append(token.text)
                if whitespace:
                    parts.append(str(whitespace))
            continue

        parts.append(str(phonemes))
        if whitespace is not None:
            if whitespace:
                parts.append(str(whitespace))
            continue

        # Fallback: add spacing based on original text when whitespace missing
        if i + 1 < len(tokens):
            next_token = tokens[i + 1]
            gap = next_token.char_start - token.char_end
            if gap > 0:
                parts.append(clean_text[token.char_end : next_token.char_start])

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


def _is_punctuation_token(token: TokenSpan) -> bool:
    """Check if a token should be treated as punctuation for output."""
    tag = token.meta.get("tag")
    if tag:
        return tag in {".", ",", ":", ";", "!", "?", "-", "'", '"', "(", ")", "PUNCT"}
    return _is_punctuation(token.text)


__all__ = [
    "phonemize_to_result",
]
