"""Pipeline-friendly phonemization API for kokorog2p.

This module provides the new span-based phonemization API that pykokoro should use.
It supports deterministic override application, per-span language switching, and
direct token ID output.
"""

import re
import threading
import unicodedata
import warnings as warnings_module
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import cache
from typing import TYPE_CHECKING, Any, Literal
from weakref import WeakKeyDictionary

from kokorog2p.integrations import coerce_override_spans
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.span_processing import (
    apply_overrides_to_tokens,
    apply_text_replacements_to_tokens,
)
from kokorog2p.stress import InvalidStressLevel, apply_stress, parse_stress_level
from kokorog2p.tokenization import (
    ensure_gtoken_positions,
    gtokens_to_tokenspans,
    tokenize_with_offsets,
    tokens_from_annotations,
)
from kokorog2p.types import (
    OverrideSpanLike,
    PhonemizeResult,
    TextReplacement,
    TokenAnnotationLike,
    TokenSpan,
)
from kokorog2p.vocab import filter_for_kokoro, phonemes_to_ids, validate_for_kokoro

if TYPE_CHECKING:
    from kokorog2p.base import G2PBase
    from kokorog2p.token import GToken


_G2P_LOCKS: "WeakKeyDictionary[object, threading.RLock]" = WeakKeyDictionary()

# Prepared text is the canonical core contract.  ``written`` remains a
# compatibility spelling for one transition period but is never semantically
# expanded by this package.
InputTextMode = Literal["written", "prepared"]


@dataclass(frozen=True)
class PreparedSpanText:
    """Text prepared only by KokoroG2P's phonological/model rules."""

    clean_text: str
    semantic_text: str
    model_text: str
    tokens: list[TokenSpan]
    warnings: list[str]
    migrated_semantics: bool


class _SpokenformRunResult(list[TextReplacement]):
    """Compatibility result for an explicitly optional Spokenform adapter."""

    def __init__(
        self,
        replacements: Sequence[TextReplacement] = (),
        warnings: Sequence[str] = (),
    ) -> None:
        super().__init__(replacements)
        self.warnings = list(warnings)


def _uses_spokenform_semantics(lang: str | None) -> bool:
    """Return false because semantic preparation is outside the core package."""
    del lang
    return False


def _g2p_input_is_prepared(*, input_mode: InputTextMode, language: str) -> bool:
    """Treat every core pipeline call as prepared text."""
    del language
    return input_mode == "prepared" or input_mode == "written"


def _get_g2p_lock(g2p: Any) -> threading.RLock:
    try:
        lock = _G2P_LOCKS.get(g2p)
        if lock is None:
            lock = threading.RLock()
            _G2P_LOCKS[g2p] = lock
        return lock
    except TypeError:
        return threading.RLock()


def _get_target_model(g2p: Any) -> str:
    if g2p is None:
        return "1.0"
    if hasattr(g2p, "get_target_model"):
        try:
            model = g2p.get_target_model()
            if model:
                return str(model)
        except Exception:  # noqa: S110
            pass
    version = getattr(g2p, "version", None)
    return str(version) if version else "1.0"


def _get_frontend_version(g2p: Any) -> str:
    return str(getattr(g2p, "version", "1.0"))


def _preserves_source_punctuation(g2p: Any) -> bool:
    capabilities = getattr(g2p, "capabilities", None)
    if callable(capabilities):
        values = capabilities()
        if isinstance(values, Mapping):
            return bool(values.get("preserve_source_punctuation"))
    return bool(getattr(g2p, "preserve_source_punctuation", False))


def _merge_target_model(current: str, candidate: str) -> str:
    if not current or current == candidate:
        return current or candidate
    if current == "1.0":
        return candidate
    if candidate == "1.0":
        return current
    raise ValueError(
        f"Incompatible target model profiles: {current!r} and {candidate!r}"
    )


def _normalize_punctuation_output(text: str) -> str:
    if not text:
        return text
    normalized = normalize_punctuation(text)
    if "-" in normalized:
        # Word-internal hyphens join compound words (e.g. "trente-sept",
        # "mother-in-law") and must survive for lexicon lookups. Remaining
        # hyphen-as-dash usage maps to the Kokoro em dash.
        normalized = _HYPHEN_AS_DASH_RE.sub("—", normalized)
    return normalized


_HYPHEN_AS_DASH_RE = re.compile(r"(?<!\w)-|-(?!\w)")


_SPACED_ELLIPSIS_RE = re.compile(r"\s*\.\s+\.\s+\.\s*")


def _normalize_source_ellipsis(text: str) -> str:
    """Normalize spaced ellipses without removing semantic symbols."""

    return _SPACED_ELLIPSIS_RE.sub("…", text)


def _realign_source_punctuation_tokens(
    tokens: list[TokenSpan],
    source_text: str,
    normalized_text: str,
) -> list[TokenSpan]:
    """Realign source tokens when model punctuation collapses a dot run."""

    if source_text == normalized_text:
        return tokens

    opcodes = SequenceMatcher(None, source_text, normalized_text).get_opcodes()
    realigned: list[TokenSpan] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if (
            index + 2 < len(tokens)
            and all(candidate.text == "." for candidate in tokens[index : index + 3])
            and _SPACED_ELLIPSIS_RE.fullmatch(
                source_text[token.char_start : tokens[index + 2].char_end]
            )
        ):
            last = tokens[index + 2]
            start = _map_position_to_normalized(token.char_start, opcodes)
            end = _map_position_to_normalized(last.char_end, opcodes)
            merged_meta = dict(token.meta)
            ext_starts = [
                int(candidate.meta.get("_extended_char_start", candidate.char_start))
                for candidate in tokens[index : index + 3]
            ]
            ext_ends = [
                int(candidate.meta.get("_extended_char_end", candidate.char_end))
                for candidate in tokens[index : index + 3]
            ]
            merged_meta["_extended_char_start"] = min(ext_starts)
            merged_meta["_extended_char_end"] = max(ext_ends)
            realigned.append(
                TokenSpan(
                    text=normalized_text[start:end],
                    char_start=start,
                    char_end=end,
                    lang=token.lang,
                    extended_text=token.extended_text,
                    meta=merged_meta,
                )
            )
            index += 3
            continue

        start = _map_position_to_normalized(token.char_start, opcodes)
        end = _map_position_to_normalized(token.char_end, opcodes)
        realigned.append(
            TokenSpan(
                text=normalized_text[start:end],
                char_start=start,
                char_end=end,
                lang=token.lang,
                extended_text=token.extended_text,
                meta=dict(token.meta),
            )
        )
        index += 1

    return realigned


def _normalize_lang(lang: str | None) -> str | None:
    if not lang:
        return None
    return lang.lower().replace("_", "-")


def _spokenform_language(lang: str | None) -> str | None:
    """Adapt Kokoro product aliases to Spokenform locale identifiers."""
    normalized = _normalize_lang(lang)
    if not normalized:
        return None
    try:
        from kokorog2p import _canonical_language

        return _canonical_language(normalized)
    except (ImportError, TypeError, ValueError):
        return normalized


@cache
def _get_abbreviation_expander(lang: str | None) -> None:
    """Deprecated compatibility hook; semantic expansion is external."""
    del lang


@cache
def _expand_abbreviation(
    token_text: str,
    before: str,
    after: str,
    lang: str | None,
) -> str | None:
    """Semantic abbreviation expansion is intentionally unavailable in core."""
    del token_text, before, after, lang
    return None


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
    if normalized.startswith("th"):
        from kokorog2p.th import ThaiNormalizer

        return ThaiNormalizer()

    return None


def _get_structured_replacements(
    text: str,
    lang: str | None,
    *,
    source_offset: int = 0,
    protected_spans: Sequence[tuple[int, int]] = (),
    expand_nums: bool = True,
) -> list[TextReplacement]:
    """Return no semantic replacements from the core G2P package."""
    del text, lang, source_offset, protected_spans, expand_nums
    return []


def _spokenform_replacements_for_run(
    text: str,
    language: str,
    *,
    source_offset: int = 0,
    protected_spans: Sequence[tuple[int, int]] = (),
    expand_nums: bool = True,
) -> _SpokenformRunResult:
    """Adapt spokenform source replacements into kokorog2p's public type."""
    spokenform_language = _spokenform_language(language) or language
    from dataclasses import replace

    from spokenform import NumberPolicy, PreparationConfig, prepare_for_kokorog2p

    config = PreparationConfig.for_kokorog2p(spokenform_language)
    if (_normalize_lang(language) or "").split("-", 1)[0] == "fr" and not expand_nums:
        config = replace(
            config,
            expand_numbers=False,
            number_policy=NumberPolicy.NONE,
        )

    prepared = prepare_for_kokorog2p(
        text,
        language=spokenform_language,
        config=config,
        protected_spans=protected_spans,
    )
    replacements: list[TextReplacement] = []
    warnings = [
        f"[SPOKENFORM] {warning}" for warning in getattr(prepared, "warnings", ())
    ]
    for item in prepared.source_replacements:
        if item.source_start < 0 or item.source_end > len(text):
            warnings.append(
                "[SPOKENFORM] source replacement has invalid bounds "
                f"[{item.source_start}:{item.source_end}] for run length {len(text)}"
            )
            continue
        if text[item.source_start : item.source_end] != item.source:
            warnings.append(
                "[SPOKENFORM] source replacement mismatch at "
                f"[{item.source_start}:{item.source_end}]: "
                f"expected {item.source!r}, got "
                f"{text[item.source_start : item.source_end]!r}"
            )
        replacements.append(
            TextReplacement(
                start=source_offset + item.source_start,
                end=source_offset + item.source_end,
                text=item.replacement,
                kind=item.kind or "spokenform",
                rule=getattr(item, "rule", None),
                language=getattr(item, "language", None),
                stages=tuple(str(stage) for stage in getattr(item, "stages", ())),
            )
        )
    return _SpokenformRunResult(replacements, warnings)


def _apply_structured_replacements_to_tokens(
    tokens: list[TokenSpan],
    clean_text: str,
    default_lang: str,
    overrides: Sequence[object] = (),
    expand_nums: bool = True,
) -> tuple[list[TokenSpan], list[str]]:
    """Apply semantic replacements independently within language runs."""

    if not tokens:
        return tokens, []

    all_warnings: list[str] = []
    processed_tokens: list[TokenSpan] = []
    run_start = 0
    protected_overrides = coerce_override_spans(overrides)

    def flush_run(start: int, end: int) -> None:
        if start >= end:
            return
        run_tokens = tokens[start:end]
        run_text_start = run_tokens[0].char_start
        run_text_end = run_tokens[-1].char_end
        run_lang = run_tokens[0].lang or default_lang
        run_protected = tuple(
            (
                max(span.char_start, run_text_start) - run_text_start,
                min(span.char_end, run_text_end) - run_text_start,
            )
            for span in protected_overrides
            if span.char_start < run_text_end and span.char_end > run_text_start
        )
        replacements = _get_structured_replacements(
            clean_text[run_text_start:run_text_end],
            run_lang,
            source_offset=run_text_start,
            protected_spans=run_protected,
            expand_nums=(
                expand_nums
                if (_normalize_lang(run_lang) or "").startswith("fr")
                else True
            ),
        )
        all_warnings.extend(getattr(replacements, "warnings", ()))
        replaced, warnings = apply_text_replacements_to_tokens(
            run_tokens,
            clean_text,
            replacements,
            default_lang=run_lang,
        )
        processed_tokens.extend(replaced)
        all_warnings.extend(warnings)

    previous_lang = (tokens[0].lang or default_lang).lower().replace("_", "-")
    for index in range(1, len(tokens)):
        current_lang = (tokens[index].lang or default_lang).lower().replace("_", "-")
        if current_lang != previous_lang:
            flush_run(run_start, index)
            run_start = index
            previous_lang = current_lang
    flush_run(run_start, len(tokens))
    return processed_tokens, all_warnings


def _apply_extended_text(
    tokens: list[TokenSpan],
    clean_text: str,
    default_lang: str,
    *,
    use_normalizer_rules: bool = True,
) -> str:
    """Apply only intrinsic frontend normalization to prepared text."""
    del default_lang
    if not tokens:
        return clean_text

    prefix = clean_text[: tokens[0].char_start]
    parts = [prefix]
    extended_pos = len(prefix)
    del use_normalizer_rules
    for index, token in enumerate(tokens):
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


def _prepare_span_text(
    clean_text: str,
    *,
    lang: str,
    overrides: Sequence[OverrideSpanLike] = (),
    annotations: Sequence[TokenAnnotationLike] | None = None,
    expand_nums: bool = True,
    use_normalizer_rules: bool = True,
    input_mode: InputTextMode = "prepared",
    source_sensitive: bool = False,
    overlap: Literal["snap", "strict"] = "snap",
) -> PreparedSpanText:
    """Prepare span text before invoking any language G2P frontend."""
    prepared_mode = input_mode == "prepared"
    migrated_semantics = not prepared_mode and _uses_spokenform_semantics(lang)
    migrated_semantics = False
    token_spans = (
        tokens_from_annotations(clean_text, annotations, lang=lang, keep_punct=True)
        if annotations is not None
        else tokenize_with_offsets(clean_text, lang=lang, keep_punct=True)
    )
    warnings: list[str] = []
    if overrides:
        token_spans, override_warnings = apply_overrides_to_tokens(
            token_spans, overrides, mode=overlap
        )
        warnings.extend(override_warnings)
    if prepared_mode:
        semantic_text = _apply_extended_text(
            token_spans,
            clean_text,
            lang,
            use_normalizer_rules=False,
        )
    else:
        token_spans, replacement_warnings = _apply_structured_replacements_to_tokens(
            token_spans,
            clean_text,
            lang,
            overrides or (),
            expand_nums=expand_nums,
        )
        warnings.extend(replacement_warnings)
        semantic_text = _apply_extended_text(
            token_spans,
            clean_text,
            lang,
            use_normalizer_rules=use_normalizer_rules,
        )
    model_text = (
        semantic_text
        if source_sensitive or not (migrated_semantics or prepared_mode)
        else _normalize_punctuation_output(semantic_text)
    )
    return PreparedSpanText(
        clean_text=clean_text,
        semantic_text=semantic_text,
        model_text=model_text,
        tokens=token_spans,
        warnings=warnings,
        migrated_semantics=migrated_semantics,
    )


def _call_g2p_without_abbreviations(  # noqa: C901
    g2p: "G2PBase",
    text: str,
    *,
    prepared: bool = False,
    annotations_provided: bool = False,
) -> list["GToken"]:
    original_expand = None
    normalizer_states: list[tuple[Any, bool | None, object | None]] = []
    prepared_states: list[tuple[Any, bool, object | None]] = []
    semantic_states: list[tuple[Any, object]] = []
    g2p_any: Any = g2p
    original_use_spacy: bool | None = None
    lock = _get_g2p_lock(g2p_any)
    with lock:
        if annotations_provided and hasattr(g2p_any, "use_spacy"):
            original_use_spacy = bool(g2p_any.use_spacy)
            g2p_any.use_spacy = False
        if prepared:
            # Let repository G2P frontends distinguish caller-prepared text
            # from their ordinary written-text convenience path.
            for target in (g2p_any, _get_g2p_normalizer(g2p_any)):
                if target is None:
                    continue
                target_any: Any = target
                try:
                    old_prepared = target_any._kokorog2p_prepared_input
                except AttributeError:
                    try:
                        target_any._kokorog2p_prepared_input = True
                    except (AttributeError, TypeError):
                        continue
                    prepared_states.append((target_any, False, None))
                else:
                    try:
                        target_any._kokorog2p_prepared_input = True
                    except (AttributeError, TypeError):
                        continue
                    prepared_states.append((target_any, True, old_prepared))
                if hasattr(target, "expand_nums"):
                    try:
                        old_expand_nums = target_any.expand_nums
                        target_any.expand_nums = False
                        semantic_states.append((target_any, old_expand_nums))
                    except (AttributeError, TypeError):
                        pass
        if hasattr(g2p_any, "expand_abbreviations"):
            original_expand = g2p_any.expand_abbreviations
            g2p_any.expand_abbreviations = False
        normalizer: Any = _get_g2p_normalizer(g2p_any)
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
            if original_use_spacy is not None:
                g2p_any.use_spacy = original_use_spacy
            if original_expand is not None:
                g2p_any.expand_abbreviations = original_expand
            for normalizer_obj, expand_value, abbrev_expander in normalizer_states:
                normalizer_any: Any = normalizer_obj
                if expand_value is not None:
                    normalizer_any.expand_abbreviations = expand_value
                if hasattr(normalizer_any, "abbrev_expander"):
                    normalizer_any.abbrev_expander = abbrev_expander
            for target, existed, old_prepared in reversed(prepared_states):
                if existed:
                    target._kokorog2p_prepared_input = old_prepared
                else:
                    try:
                        delattr(target, "_kokorog2p_prepared_input")
                    except AttributeError:
                        pass
            for target, old_expand_nums in reversed(semantic_states):
                target.expand_nums = old_expand_nums


def _get_g2p_normalizer(g2p: Any) -> Any | None:
    normalizer: Any = getattr(g2p, "_normalizer", None)
    if normalizer is None and hasattr(g2p, "normalizer"):
        try:
            normalizer = g2p.normalizer
        except Exception:
            normalizer = None
    return normalizer


def _normalize_for_g2p_alignment(
    text: str,
    g2p: "G2PBase",
    *,
    input_mode: InputTextMode = "prepared",
) -> str:
    normalizer = _get_g2p_normalizer(g2p)
    if normalizer is None or not text:
        return text
    lock = _get_g2p_lock(g2p)

    with lock:
        original_expand = None
        original_abbrev = None

        if hasattr(normalizer, "expand_abbreviations"):
            original_expand = normalizer.expand_abbreviations
            normalizer.expand_abbreviations = False
            if hasattr(normalizer, "abbrev_expander"):
                original_abbrev = normalizer.abbrev_expander
                normalizer.abbrev_expander = None

        try:
            normalize_for_g2p = getattr(normalizer, "normalize_for_g2p", None)
            if callable(normalize_for_g2p):
                return normalize_for_g2p(text)
            if input_mode == "prepared":
                # Unknown normalizers may combine typography with semantics;
                # do not invoke that ambiguous fallback for prepared text.
                return text
            return normalizer(text)
        finally:
            if original_expand is not None:
                normalizer.expand_abbreviations = original_expand
            if hasattr(normalizer, "abbrev_expander"):
                normalizer.abbrev_expander = original_abbrev


def _map_position_to_normalized(
    pos: int, opcodes: Sequence[tuple[str, int, int, int, int]]
) -> int:
    if not opcodes:
        return pos

    for tag, i1, i2, j1, j2 in opcodes:
        if pos < i1:
            return pos + (j1 - i1)
        if i1 <= pos <= i2:
            if tag == "equal":
                return j1 + (pos - i1)
            if tag == "insert":
                return j1
            if tag == "delete":
                return j1
            if i2 == i1:
                return j1
            rel = pos - i1
            orig_len = i2 - i1
            new_len = j2 - j1
            return j1 + round(rel * new_len / orig_len)

    last_i2 = opcodes[-1][2]
    last_j2 = opcodes[-1][4]
    return pos + (last_j2 - last_i2)


def _align_tokens_to_normalized_text(
    tokens: list[TokenSpan],
    original_text: str,
    normalized_text: str,
) -> list[str]:
    warnings: list[str] = []
    if original_text == normalized_text:
        return warnings
    if len(original_text) == len(normalized_text):
        return warnings

    opcodes = SequenceMatcher(None, original_text, normalized_text).get_opcodes()
    prev_end = 0
    norm_len = len(normalized_text)

    for token in tokens:
        token_start = token.meta.get("_extended_char_start", token.char_start)
        token_end = token.meta.get("_extended_char_end", token.char_end)
        mapped_start = _map_position_to_normalized(token_start, opcodes)
        mapped_end = _map_position_to_normalized(token_end, opcodes)
        mapped_start = max(0, min(mapped_start, norm_len))
        mapped_end = max(0, min(mapped_end, norm_len))

        if mapped_start < prev_end:
            warnings.append(
                f"[ALIGNMENT] token '{token.text}' [{token_start}:{token_end}] "
                f"mapped start {mapped_start} < {prev_end} (clamped)"
            )
            mapped_start = prev_end

        if mapped_end < mapped_start:
            warnings.append(
                f"[ALIGNMENT] token '{token.text}' [{token_start}:{token_end}] "
                f"mapped end {mapped_end} < {mapped_start} (clamped)"
            )
            mapped_end = mapped_start

        if mapped_end == mapped_start and token_end > token_start:
            warnings.append(
                f"[ALIGNMENT] token '{token.text}' [{token_start}:{token_end}] "
                f"mapped to empty span at {mapped_start}"
            )

        token.meta["_extended_char_start"] = mapped_start
        token.meta["_extended_char_end"] = mapped_end
        prev_end = mapped_end

    return warnings


def phonemize_to_result(
    clean_text: str,
    *,
    lang: str | None = None,
    overrides: Sequence[OverrideSpanLike] | None = None,
    annotations: Sequence[TokenAnnotationLike] | None = None,
    return_ids: bool = True,
    return_phonemes: bool = True,
    alignment: Literal["span", "legacy"] = "span",
    overlap: Literal["snap", "strict"] = "snap",
    use_normalizer_rules: bool = True,
    g2p: "G2PBase | None" = None,
    lexicons: str | Sequence[str] | None = None,
    g2p_options: dict[str, Any] | None = None,
    input_mode: InputTextMode = "prepared",
    strict_stress: bool = False,
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
        g2p_options: Optional factory options to use when loading G2P instances
            for language-specific override spans.

        strict_stress: Whether invalid stress metadata raises instead of producing a
            warning.
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

    if input_mode not in ("written", "prepared"):
        raise ValueError(f"Unsupported input_mode: {input_mode!r}")
    if input_mode == "written":
        warnings_module.warn(
            "Semantic written-to-spoken preparation is deprecated in KokoroG2P. "
            "Run Spokenform first and use phonemize_prepared().",
            DeprecationWarning,
            stacklevel=2,
        )
    prepared_mode = input_mode == "prepared"
    lang = lang or "en-us"
    warnings: list[str] = []
    result_clean_text = clean_text

    # Resolve the frontend before normalization so source-sensitive languages
    # can classify punctuation using the user's original text.
    if g2p is None:
        options = dict(g2p_options or {})
        if lexicons is not None:
            options["lexicons"] = lexicons
        g2p = get_g2p(lang, **options)
        g2p_options = options
    source_sensitive = _preserves_source_punctuation(g2p)

    # Written mode preserves the source for Spokenform before model punctuation
    # cleanup. Prepared mode keeps the caller's text as the coordinate authority.
    migrated_semantics = not prepared_mode and _uses_spokenform_semantics(lang)
    if not prepared_mode and not migrated_semantics and not source_sensitive:
        clean_text = normalize_punctuation(clean_text)
        result_clean_text = clean_text
    g2p_token_spans: list[TokenSpan]
    extended_text: str = ""

    if alignment == "span":
        # Prepare semantic and model text before the G2P frontend.
        prepared_span = _prepare_span_text(
            clean_text,
            lang=lang,
            annotations=annotations,
            overrides=overrides or (),
            expand_nums=bool(getattr(g2p, "expand_nums", True)),
            use_normalizer_rules=use_normalizer_rules,
            input_mode=input_mode,
            source_sensitive=source_sensitive,
            overlap=overlap,
        )
        token_spans = prepared_span.tokens
        warnings.extend(prepared_span.warnings)
        semantic_text = prepared_span.semantic_text
        model_text = prepared_span.model_text
        normalized_text = _normalize_for_g2p_alignment(
            model_text, g2p, input_mode=input_mode
        )
        alignment_warnings = _align_tokens_to_normalized_text(
            token_spans, semantic_text, normalized_text
        )
        warnings.extend(alignment_warnings)
        if migrated_semantics:
            result_clean_text = _normalize_source_ellipsis(clean_text)
            token_spans = _realign_source_punctuation_tokens(
                token_spans, clean_text, result_clean_text
            )
        extended_text = normalized_text
        g2p_input_prepared = True
        gtokens = _call_g2p_without_abbreviations(
            g2p,
            extended_text,
            prepared=g2p_input_prepared,
            annotations_provided=annotations is not None,
        )
        warnings.extend(str(warning) for warning in getattr(g2p, "warnings", ()))
        ensure_gtoken_positions(gtokens, extended_text)
        g2p_token_spans = gtokens_to_tokenspans(gtokens, extended_text)
    else:
        # Legacy: use G2P's tokenization and offsets
        gtokens = _call_g2p_without_abbreviations(
            g2p,
            clean_text,
            prepared=True,
            annotations_provided=annotations is not None,
        )
        ensure_gtoken_positions(gtokens, clean_text)
        g2p_token_spans = gtokens_to_tokenspans(gtokens, clean_text)
        token_spans = g2p_token_spans

        if overrides:
            token_spans, override_warnings = apply_overrides_to_tokens(
                token_spans, overrides, mode=overlap
            )
            warnings.extend(override_warnings)
        if migrated_semantics:
            result_clean_text = _normalize_source_ellipsis(clean_text)

    # Phonemize tokens based on language and overrides
    phonemized_tokens, phonemize_warnings, target_model = _phonemize_token_spans(
        token_spans,
        g2p_token_spans,
        g2p,
        lang,
        g2p_options=g2p_options,
        input_mode=input_mode,
        strict_stress=strict_stress,
    )
    warnings.extend(phonemize_warnings)

    # Build phoneme string if needed for output OR for IDs
    phoneme_str: str = ""
    if return_phonemes or return_ids:
        phoneme_str = _build_phoneme_string(phonemized_tokens, result_clean_text)

    phonemes: str = phoneme_str if return_phonemes else ""

    # Build token IDs if requested (independent of return_phonemes)
    token_ids: list[int] = []
    if return_ids and phoneme_str is not None:
        is_valid, invalid = validate_for_kokoro(phoneme_str, model=target_model)
        if not is_valid:
            warnings.append(
                "[VOCAB] invalid chars for model {} dropped: {}".format(
                    target_model,
                    "".join(sorted(set(invalid))),
                )
            )
            phoneme_str = filter_for_kokoro(
                phoneme_str, replacement="", model=target_model
            )
        try:
            token_ids = phonemes_to_ids(phoneme_str, model=target_model)
        except Exception as e:
            warnings.append(
                f"[VOCAB] failed to convert phonemes to IDs "
                f"for model {target_model}: {e}"
            )
            token_ids = []

    if warnings:
        seen: set[str] = set()
        deduped: list[str] = []
        for warning in warnings:
            if warning not in seen:
                deduped.append(warning)
                seen.add(warning)
        warnings = deduped

    return PhonemizeResult(
        clean_text=result_clean_text,
        tokens=phonemized_tokens,
        extended_text=extended_text,
        phonemes=phonemes,
        token_ids=token_ids,
        warnings=warnings,
    )


def _stress_vowels(language: str) -> frozenset[str]:
    """Return the final-phoneme vowel inventory for a language."""
    normalized = language.lower().replace("_", "-")
    if normalized.startswith("de"):
        from kokorog2p.de.stress import GERMAN_VOWELS

        return GERMAN_VOWELS
    if normalized.startswith("en"):
        from kokorog2p.en.lexicon import VOWELS

        return VOWELS
    return frozenset("aɑeɛiɪoɔøœuʊyəɜɐAIOQWY")


def _apply_token_stress(
    token: TokenSpan,
    phonemes: str,
    *,
    language: str,
    strict: bool,
    warnings: list[str],
) -> str:
    """Apply a token's explicit stress override after pronunciation resolution."""
    stress_value = token.meta.get("stress")
    if not stress_value or not phonemes or _is_punctuation_token(token):
        return phonemes
    if _is_punctuation(phonemes) or phonemes == "?":
        return phonemes
    ph_override = str(token.meta.get("ph", ""))
    if "ph" in token.meta and any(character.isspace() for character in ph_override):
        message = (
            f"[STRESS] cannot apply stress to collapsed multi-word ph override "
            f"for token '{token.text}' [{token.char_start}:{token.char_end}]"
        )
        if strict:
            raise InvalidStressLevel(message)
        warnings.append(message)
        return phonemes
    try:
        level = parse_stress_level(stress_value)
    except InvalidStressLevel as exc:
        if strict:
            raise
        warnings.append(
            f"[STRESS] {exc} for token '{token.text}' "
            f"[{token.char_start}:{token.char_end}]"
        )
        return phonemes
    return apply_stress(phonemes, level, vowels=_stress_vowels(language))


def _phonemize_token_spans(  # noqa: C901
    token_spans: list[TokenSpan],
    g2p_token_spans: list[TokenSpan],
    g2p: "G2PBase",
    default_lang: str,
    *,
    g2p_options: dict[str, Any] | None = None,
    input_mode: InputTextMode = "written",
    strict_stress: bool = False,
) -> tuple[list[TokenSpan], list[str], str]:
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
    target_model = _get_target_model(g2p)
    g2p_index = 0
    carry_alnum_end: int | None = None

    for token in token_spans:
        # Determine language for this token
        token_lang = token.lang or default_lang
        token_start = token.meta.get("_extended_char_start", token.char_start)
        token_end = token.meta.get("_extended_char_end", token.char_end)
        token_is_punct = _is_punctuation_token(token)
        use_overlap_mapping = token_lang == default_lang and "ph" not in token.meta
        mapped_parts: list[str] = []
        carried_from_previous = carry_alnum_end
        if carried_from_previous is not None and token_start >= carried_from_previous:
            carry_alnum_end = None
            carried_from_previous = None

        consumed_by_previous_g2p = (
            carried_from_previous is not None
            and token_start < carried_from_previous
            and token_end <= carried_from_previous
            and token_lang == default_lang
            and "ph" not in token.meta
        )
        if (
            carried_from_previous is not None
            and token_start < carried_from_previous < token_end
        ):
            warnings.append(
                f"[ALIGNMENT] token '{token.text}' "
                f"[{token_start}:{token_end}] partially overlaps previously "
                f"consumed G2P span ending at {carried_from_previous}"
            )
        elif (
            carried_from_previous is not None
            and token_start < carried_from_previous
            and token_end <= carried_from_previous
            and not consumed_by_previous_g2p
        ):
            warnings.append(
                f"[ALIGNMENT] token '{token.text}' "
                f"[{token_start}:{token_end}] remains explicit within previously "
                f"consumed G2P span ending at {carried_from_previous}"
            )

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
            if whitespace is not None and overlap_span.char_end == token_end:
                mapped_whitespace = str(whitespace)
            if mapped_tag is None:
                tag = overlap_span.meta.get("tag")
                if tag:
                    mapped_tag = str(tag)
            scan_index += 1
        if overlap_spans:
            overlap_alnum_spans = [
                span for span in overlap_spans if any(c.isalnum() for c in span.text)
            ]
            if overlap_alnum_spans:
                owner_token_text = (token.extended_text or token.text).casefold()
                furthest_alnum_span = max(
                    overlap_alnum_spans,
                    key=lambda span: span.char_end,
                )
                owner_span = next(
                    (
                        span
                        for span in overlap_alnum_spans
                        if owner_token_text
                        and span.text.casefold().startswith(owner_token_text)
                    ),
                    None,
                )
                if (
                    owner_span is not None
                    and not token_is_punct
                    and use_overlap_mapping
                    and furthest_alnum_span.char_end > token_end
                ):
                    carry_alnum_end = max(
                        carry_alnum_end or 0,
                        furthest_alnum_span.char_end,
                    )
                    owner_whitespace = furthest_alnum_span.meta.get("whitespace")
                    if owner_whitespace is not None:
                        mapped_whitespace = str(owner_whitespace)
        if any(span.meta.get("drop") for span in overlap_spans):
            token.meta["_drop"] = True
        drop_due_to_carry = consumed_by_previous_g2p
        if drop_due_to_carry:
            token.meta["_drop"] = True
            overlap_spans = []
            mapped_whitespace = None
            mapped_tag = None
            g2p_index = scan_index
        elif token_is_punct and overlap_spans:
            overlap_has_alnum = any(
                any(c.isalnum() for c in span.text) for span in overlap_spans
            )
            if overlap_has_alnum:
                token.meta["_drop"] = True
                first_alnum = next(
                    (
                        idx
                        for idx, span in enumerate(overlap_spans)
                        if any(c.isalnum() for c in span.text)
                    ),
                    None,
                )
                if first_alnum is not None:
                    g2p_index = g2p_index + first_alnum
                overlap_spans = [
                    span
                    for span in overlap_spans
                    if not any(c.isalnum() for c in span.text)
                ]
                mapped_tag = None
            else:
                g2p_index = scan_index
        else:
            g2p_index = scan_index

        # Get G2P instance for this language
        if token_lang not in g2p_cache:
            try:
                g2p_cache[token_lang] = get_g2p(
                    token_lang,
                    version=_get_frontend_version(g2p),
                    **(g2p_options or {}),
                )
            except Exception as e:
                warnings.append(
                    f"[G2P] failed to load language '{token_lang}' for token "
                    f"'{token.text}' [{token.char_start}:{token.char_end}]: {e}"
                )
                # Fall back to default language
                token_lang = default_lang

        token_g2p = g2p_cache[token_lang]
        target_model = _merge_target_model(target_model, _get_target_model(token_g2p))

        # Check if phoneme override is present
        if drop_due_to_carry:
            phonemes = ""
        elif "ph" in token.meta:
            # Use override phonemes
            phonemes = str(token.meta["ph"])
        elif token_lang != default_lang:
            # Re-phonemize using language-specific G2P
            try:
                token_text = token.extended_text or token.text
                gtokens = _call_g2p_without_abbreviations(
                    token_g2p,
                    token_text,
                    prepared=_g2p_input_is_prepared(
                        input_mode=input_mode, language=token_lang
                    ),
                )
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
                            f"[G2P] no phonemes for token '{token.text}' "
                            f"[{token.char_start}:{token.char_end}] lang='{token_lang}'"
                        )
            except Exception as e:
                warnings.append(
                    f"[G2P] phonemization failed for token '{token.text}' "
                    f"[{token.char_start}:{token.char_end}] lang='{token_lang}': {e}"
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
            annotation_tag = token.meta.get("tag") or token.meta.get("pos")
            if annotation_tag and not token_is_punct and "ph" not in token.meta:
                try:
                    annotated = token_g2p.lookup(
                        token.extended_text or token.text, str(annotation_tag)
                    )
                except (AttributeError, TypeError, ValueError):
                    annotated = None
                if annotated:
                    phonemes = annotated
            if not phonemes and token.text.strip() and not _is_punctuation(token.text):
                # fallback: re-phonemize token directly
                try:
                    token_text = token.extended_text or token.text
                    gtokens = token_g2p(token_text)
                    phoneme_parts = []
                    for gt in gtokens:
                        if gt.phonemes:
                            phoneme_parts.append(gt.phonemes)
                            if gt.whitespace:
                                phoneme_parts.append(gt.whitespace)
                    phonemes = "".join(phoneme_parts).strip()
                except Exception as e:
                    warnings.append(
                        f"[G2P] fallback phonemization failed for token "
                        f"'{token.text}' [{token.char_start}:{token.char_end}]: {e}"
                    )

        phonemes = _apply_token_stress(
            token,
            phonemes,
            language=token_lang,
            strict=strict_stress,
            warnings=warnings,
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

    return phonemized_tokens, warnings, target_model


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
        if token.meta.get("_drop"):
            continue
        phonemes = token.meta.get("phonemes", "")
        token_is_punct = _is_punctuation_token(token)
        whitespace = token.meta.get("whitespace")
        if whitespace == "" and token.extended_text:
            whitespace = None

        normalized_token_text = _normalize_punctuation_output(token.text)
        if token_is_punct and phonemes:
            normalized_phonemes = _normalize_punctuation_output(str(phonemes))
            if _is_quote_punctuation(normalized_phonemes) and _is_quote_punctuation(
                normalized_token_text
            ):
                phonemes = normalized_phonemes
            elif (
                normalized_token_text
                and normalized_phonemes != normalized_token_text
                and _is_punctuation(normalized_phonemes)
            ):
                phonemes = normalized_token_text
            else:
                phonemes = normalized_phonemes

        if not phonemes:
            # No phonemes - might be punctuation or failed phonemization
            # Check if it's punctuation and include as-is
            if token_is_punct:
                if _is_quote_punctuation(normalized_token_text):
                    continue
                if normalized_token_text.strip():
                    parts.append(normalized_token_text)
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
                start = max(0, min(token.char_end, len(clean_text)))
                end = max(0, min(next_token.char_start, len(clean_text)))
                if end > start:
                    parts.append(clean_text[start:end])

    return "".join(parts).strip()


def _is_punctuation(text: str) -> bool:
    if not text:
        return False
    s = text.strip()
    if not s:
        return False
    # treat as punctuation if every char is Unicode punctuation or symbol
    return all(unicodedata.category(ch)[0] in {"P", "S"} for ch in s)


def _is_quote_punctuation(text: str) -> bool:
    if not text:
        return False
    return any(ch in {'"', "\u201c", "\u201d", "'"} for ch in text.strip())


def _is_punctuation_token(token: TokenSpan) -> bool:
    """Check if a token should be treated as punctuation for output."""
    tag = token.meta.get("tag")
    if tag:
        return tag in {".", ",", ":", ";", "!", "?", "-", "'", '"', "(", ")", "PUNCT"}
    return _is_punctuation(token.text)


__all__ = [
    "phonemize_to_result",
]
