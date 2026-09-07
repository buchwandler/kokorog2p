"""Conservative, selected-lexicon-evidence-based pronunciation routing."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from kokorog2p.language_codes import normalize_language_code, supported_languages
from kokorog2p.lexicons.evidence import LexiconEvidence
from kokorog2p.types import LanguageFragment, LanguageRoute, TokenSpan
from kokorog2p.vocab import validate_for_kokoro

if TYPE_CHECKING:
    from kokorog2p.base import G2PBase


@dataclass(frozen=True, slots=True)
class LanguageRoutingConfig:
    """Configuration for automatic pronunciation-language routing."""

    mode: Literal["off", "auto"] = "off"
    languages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.mode not in ("off", "auto"):
            raise ValueError("language routing mode must be 'off' or 'auto'")
        raw_languages: Any = self.languages
        if isinstance(raw_languages, str):
            raise TypeError(
                "language routing languages must be a sequence, not a string"
            )
        supported = set(supported_languages())
        canonical: list[str] = []
        for language in raw_languages:
            normalized = normalize_language_code(language)
            if normalized not in supported:
                raise ValueError(f"unsupported language for routing: {language!r}")
            if normalized not in canonical:
                canonical.append(normalized)
        object.__setattr__(self, "languages", tuple(canonical))
        if self.mode == "auto" and len(canonical) < 2:
            raise ValueError(
                "automatic language routing requires at least two languages"
            )


def coerce_language_routing(
    config: LanguageRoutingConfig | Mapping[str, Any] | None,
    *,
    default_language: str,
) -> LanguageRoutingConfig:
    """Normalize a public routing argument and validate its document language."""
    if config is None:
        result = LanguageRoutingConfig()
    elif isinstance(config, LanguageRoutingConfig):
        result = config
    elif isinstance(config, Mapping):
        result = LanguageRoutingConfig(
            mode=config.get("mode", "off"),
            languages=tuple(config.get("languages", ())),
        )
    else:
        raise TypeError(
            "language_routing must be a LanguageRoutingConfig, mapping, or None"
        )
    if result.mode == "auto":
        normalized_default = normalize_language_code(default_language)
        if normalized_default not in result.languages:
            raise ValueError(
                f"default language {default_language!r} is not in the routing allowlist"
            )
    return result


@dataclass(frozen=True, slots=True)
class LanguageRoutingResult:
    """Tokens and diagnostics produced by one routing pass."""

    tokens: tuple[TokenSpan, ...]
    routes: tuple[LanguageRoute, ...] = ()
    warnings: tuple[str, ...] = ()


def _valid_for_target(phonemes: str, target_model: str) -> bool:
    """Return whether a candidate pronunciation fits a Kokoro vocabulary."""
    valid, _ = validate_for_kokoro(phonemes, model=target_model)
    return valid


def _is_eligible(token: TokenSpan) -> bool:
    return bool(token.text.strip()) and any(
        character.isalnum() for character in token.text
    )


def _fragment(
    start: int,
    end: int,
    source_text: str,
    language: str,
    kind: Literal["whole-token", "compound-root", "stem", "affix"],
    evidence: LexiconEvidence | None = None,
) -> LanguageFragment:
    return LanguageFragment(
        start,
        end,
        source_text[start:end],
        language,
        "auto",
        kind,
        None if evidence is None else evidence.lexicon_id,
        None if evidence is None else evidence.kind,
        None if evidence is None else evidence.rating,
    )


def _default_fragment(
    token: TokenSpan, language: str, evidence: LexiconEvidence | None = None
) -> LanguageFragment:
    return _fragment(
        token.char_start,
        token.char_end,
        token.text,
        language,
        "whole-token",
        evidence,
    )


def _evidence_cached(
    evidence: Callable[[str, str, str | None], LexiconEvidence | None],
) -> Callable[[str, str, str | None], LexiconEvidence | None]:
    cache: dict[tuple[str, str, str | None], LexiconEvidence | None] = {}

    def cached(
        language: str, word: str, tag: str | None = None
    ) -> LexiconEvidence | None:
        key = (normalize_language_code(language), word.casefold(), tag)
        if key not in cache:
            cache[key] = evidence(*key)
        return cache[key]

    return cached


def _realization_cached(
    realize: Callable[[str, str], str | None],
) -> Callable[[str, str], str | None]:
    cache: dict[tuple[str, str], str | None] = {}

    def cached(language: str, word: str) -> str | None:
        key = (normalize_language_code(language), word.casefold())
        if key not in cache:
            cache[key] = realize(*key)
        return cache[key]

    return cached


def route_languages(  # noqa: C901
    text: str,
    tokens: Sequence[TokenSpan],
    *,
    default_language: str,
    config: LanguageRoutingConfig,
    resolve_g2p: Callable[[str], G2PBase],
    fixed_target_model: bool = False,
    target_model: str,
    protected_ranges: Sequence[tuple[int, int]] = (),
) -> LanguageRoutingResult:
    """Route eligible tokens using selected lexical evidence and bounded analysis."""
    default = normalize_language_code(default_language)
    if config.mode == "off":
        return LanguageRoutingResult(tuple(tokens))
    allowed = config.languages
    protected = tuple(protected_ranges)
    g2ps: dict[str, G2PBase] = {}
    resolver_failures: dict[str, str] = {}

    def evidence_uncaught(
        language: str, word: str, tag: str | None = None
    ) -> LexiconEvidence | None:
        try:
            canonical = normalize_language_code(language)
            if canonical not in g2ps:
                g2ps[canonical] = resolve_g2p(canonical)
            return g2ps[canonical].lexicon_evidence(word, tag)
        except Exception as exc:
            resolver_failures[normalize_language_code(language)] = str(exc)
            raise

    def realize_uncaught(language: str, word: str) -> str | None:
        try:
            canonical = normalize_language_code(language)
            if canonical not in g2ps:
                g2ps[canonical] = resolve_g2p(canonical)
            return g2ps[canonical].lookup(word)
        except Exception as exc:
            resolver_failures[normalize_language_code(language)] = str(exc)
            raise

    evidence_cache = _evidence_cached(evidence_uncaught)
    realization_cache = _realization_cached(realize_uncaught)
    result: list[TokenSpan] = []
    routes: list[LanguageRoute] = []
    warnings: list[str] = []

    def candidate_evidence(
        language: str, word: str, tag: str | None = None
    ) -> LexiconEvidence | None:
        try:
            return evidence_cache(language, word, tag)
        except Exception:
            return None

    def candidate_realization(language: str, word: str) -> str | None:
        try:
            return realization_cache(language, word)
        except Exception:
            return None

    for token in tokens:
        if not _is_eligible(token):
            result.append(token)
            continue
        if any(
            start < token.char_end and end > token.char_start
            for start, end in protected
        ):
            result.append(token)
            continue

        word = token.text
        tag = token.meta.get("tag") or token.meta.get("pos")
        tag = None if tag is None else str(tag)
        default_evidence = candidate_evidence(default, word, tag)
        foreign_evidence = [
            (language, candidate_evidence(language, word, tag))
            for language in allowed
            if language != default
        ]
        foreign_hits = [
            (language, evidence)
            for language, evidence in foreign_evidence
            if evidence is not None
        ]
        selected_language = default
        selected_evidence = default_evidence
        fragments: Sequence[LanguageFragment] | None = None
        reason = "default language"
        confidence = "default"

        if default_evidence is not None:
            reason = "exact default-language lexicon evidence"
            confidence = "high"
        elif len(foreign_hits) == 1:
            selected_language, selected_evidence = foreign_hits[0]
            reason = "unique foreign selected-lexicon evidence"
            confidence = "high"
            fragments = (
                _fragment(
                    token.char_start,
                    token.char_end,
                    text,
                    selected_language,
                    "whole-token",
                    selected_evidence,
                ),
            )
        elif not foreign_hits:
            fragments = _try_pair_decomposition(
                token,
                default,
                allowed,
                lambda language, value: candidate_evidence(language, value),
            )
            if fragments:
                selected_language = default
                reason = "unique DE/EN lexical decomposition"
                confidence = "high"

        if fragments is None:
            fragments = (
                _default_fragment(token, selected_language, selected_evidence),
            )

        if fixed_target_model and selected_language != default:
            incompatible = [
                fragment
                for fragment in fragments
                if fragment.language != default
                and fragment.kind != "affix"
                and not _compatible_fragment(
                    fragment, candidate_realization, target_model
                )
            ]
            if incompatible:
                warnings.append(
                    "[ROUTING] automatic route rejected: pronunciation incompatible "
                    f"with fixed target model '{target_model}' despite valid "
                    "lexicon evidence"
                )
                selected_language = default
                selected_evidence = default_evidence
                fragments = (_default_fragment(token, default, default_evidence),)
                reason = "default language after target-model incompatibility"
                confidence = "default"

        if selected_language == default and len(fragments) == 1:
            result.append(
                _mark_token(token, default, "auto", reason, selected_evidence)
            )
        else:
            for fragment in fragments:
                fragment_meta = {
                    **token.meta,
                    "language_source": "auto",
                    "language_reason": reason,
                    "_route_fragment": True,
                    "_route_kind": fragment.kind,
                }
                if fragment.evidence_lexicon_id is not None:
                    fragment_meta["_evidence_lexicon_id"] = fragment.evidence_lexicon_id
                    fragment_meta["_evidence_kind"] = fragment.evidence_kind
                    fragment_meta["_evidence_rating"] = fragment.evidence_rating
                if fragment.phonemes is not None:
                    fragment_meta["ph"] = fragment.phonemes
                result.append(
                    TokenSpan(
                        text=text[fragment.char_start : fragment.char_end],
                        char_start=fragment.char_start,
                        char_end=fragment.char_end,
                        lang=fragment.language,
                        meta=fragment_meta,
                    )
                )
        routes.append(
            LanguageRoute(
                token.char_start,
                token.char_end,
                text[token.char_start : token.char_end],
                default,
                tuple(fragments),
                reason,
                confidence,
            )
        )
    for language, error in resolver_failures.items():
        warnings.append(
            f"[ROUTING] resolver failed for language '{language}'; "
            f"using default language: {error}"
        )
    return LanguageRoutingResult(tuple(result), tuple(routes), tuple(warnings))


def _compatible_fragment(
    fragment: LanguageFragment,
    realize: Callable[[str, str], str | None],
    target_model: str,
) -> bool:
    pronunciation = realize(fragment.language, fragment.text)
    return pronunciation is not None and _valid_for_target(pronunciation, target_model)


def _try_pair_decomposition(
    token: TokenSpan,
    default_language: str,
    languages: tuple[str, ...],
    evidence: Callable[[str, str], LexiconEvidence | None],
) -> Sequence[LanguageFragment] | None:
    if default_language not in {"de-de", "en-us"} or not {
        "de-de",
        "en-us",
    }.issubset(set(languages)):
        return None
    from kokorog2p.language_pairs.de_en import decompose_token

    return decompose_token(
        token,
        default_language=default_language,
        candidate_languages=languages,
        evidence=evidence,
    )


def _mark_token(
    token: TokenSpan,
    language: str,
    source: str,
    reason: str,
    evidence: LexiconEvidence | None = None,
) -> TokenSpan:
    return TokenSpan(
        text=token.text,
        char_start=token.char_start,
        char_end=token.char_end,
        lang=token.lang if token.lang is not None else None,
        extended_text=token.extended_text,
        meta={
            **token.meta,
            "language_source": source,
            "language_reason": reason,
            **(
                {
                    "_evidence_lexicon_id": evidence.lexicon_id,
                    "_evidence_kind": evidence.kind,
                    "_evidence_rating": evidence.rating,
                }
                if evidence is not None
                else {}
            ),
        },
    )


__all__ = [
    "LanguageRoutingConfig",
    "LanguageRoutingResult",
    "coerce_language_routing",
    "route_languages",
]
