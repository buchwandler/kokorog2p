"""Conservative, lexical-evidence-based pronunciation language routing."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from kokorog2p.language_codes import normalize_language_code
from kokorog2p.types import LanguageFragment, LanguageRoute, TokenSpan
from kokorog2p.vocab import validate_for_kokoro

if TYPE_CHECKING:
    from kokorog2p.base import G2PBase


_SUPPORTED_LANGUAGES = frozenset(
    {
        "en-us",
        "en-gb",
        "de-de",
        "fr-fr",
        "es-es",
        "it-it",
        "pt-br",
        "cs-cz",
        "vi-vn",
        "ko-kr",
        "he",
        "zh",
        "ja-jp",
        "ar",
        "sv-se",
        "th-th",
        "ru-ru",
        "kk",
    }
)


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
        canonical: list[str] = []
        for language in raw_languages:
            normalized = normalize_language_code(language)
            if normalized not in _SUPPORTED_LANGUAGES:
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
) -> LanguageFragment:
    return LanguageFragment(start, end, source_text[start:end], language, "auto", kind)


def _default_fragment(token: TokenSpan, language: str) -> LanguageFragment:
    return _fragment(
        token.char_start, token.char_end, token.text, language, "whole-token"
    )


def _lookup_cached(
    lookup: Callable[[str, str], str | None],
) -> Callable[[str, str], str | None]:
    cache: dict[tuple[str, str], str | None] = {}

    def cached(language: str, word: str) -> str | None:
        key = (normalize_language_code(language), word.casefold())
        if key not in cache:
            cache[key] = lookup(*key)
        return cache[key]

    return cached


def route_languages(
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
    """Route eligible tokens using exact lexicon hits and bounded pair analysis."""
    default = normalize_language_code(default_language)
    if config.mode == "off":
        return LanguageRoutingResult(tuple(tokens))
    allowed = config.languages
    protected = tuple(protected_ranges)
    g2ps: dict[str, G2PBase] = {}
    resolver_failures: dict[str, str] = {}

    def lookup_uncaught(language: str, word: str) -> str | None:
        try:
            return _lookup(g2ps, resolve_g2p, language, word)
        except Exception as exc:
            resolver_failures[language] = str(exc)
            raise

    lookup_cache = _lookup_cached(lookup_uncaught)
    result: list[TokenSpan] = []
    routes: list[LanguageRoute] = []
    warnings: list[str] = []

    def candidate_lookup(language: str, word: str) -> str | None:
        pronunciation = _safe_lookup(lookup_cache, language, word)
        if (
            pronunciation is not None
            and fixed_target_model
            and not _valid_for_target(pronunciation, target_model)
        ):
            return None
        return pronunciation

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
        default_hit = candidate_lookup(default, word)
        foreign_hits = [
            language
            for language in allowed
            if language != default and candidate_lookup(language, word) is not None
        ]
        selected_language = default
        fragments: Sequence[LanguageFragment] | None = None
        reason = "default language"
        confidence = "default"
        if default_hit is not None:
            reason = "exact default-language lexicon hit"
            confidence = "high"
        elif len(foreign_hits) == 1:
            selected_language = foreign_hits[0]
            reason = "unique foreign exact lexicon hit"
            confidence = "high"
            fragments = (
                _fragment(
                    token.char_start,
                    token.char_end,
                    text,
                    selected_language,
                    "whole-token",
                ),
            )
        elif not foreign_hits:
            fragments = _try_pair_decomposition(
                token, default, allowed, candidate_lookup
            )
            if fragments:
                selected_language = default
                reason = "unique DE/EN lexical decomposition"
                confidence = "high"
        if fragments is None:
            fragments = (
                _fragment(
                    token.char_start,
                    token.char_end,
                    text,
                    selected_language,
                    "whole-token",
                ),
            )
        if (
            selected_language == default
            and len(fragments) == 1
            and fragments[0].language == default
        ):
            result.append(_mark_token(token, default, "auto", reason))
        else:
            for fragment in fragments:
                fragment_meta = {
                    **token.meta,
                    "language_source": "auto",
                    "language_reason": reason,
                    "_route_fragment": True,
                    "_route_kind": fragment.kind,
                }
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


def _lookup(
    g2ps: dict[str, G2PBase],
    resolve_g2p: Callable[[str], G2PBase],
    language: str,
    word: str,
) -> str | None:
    if language not in g2ps:
        g2ps[language] = resolve_g2p(language)
    return g2ps[language].lookup(word)


def _safe_lookup(
    lookup: Callable[[str, str], str | None], language: str, word: str
) -> str | None:
    try:
        return lookup(language, word)
    except Exception:
        return None


def _try_pair_decomposition(
    token: TokenSpan,
    default_language: str,
    languages: tuple[str, ...],
    lookup: Callable[[str, str], str | None],
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
        lookup=lookup,
    )


def _mark_token(token: TokenSpan, language: str, source: str, reason: str) -> TokenSpan:
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
        },
    )


__all__ = [
    "LanguageRoutingConfig",
    "LanguageRoutingResult",
    "coerce_language_routing",
    "route_languages",
]
