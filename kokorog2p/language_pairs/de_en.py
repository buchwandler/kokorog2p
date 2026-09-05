"""Bounded German and English compound and morphology analysis."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from kokorog2p.types import LanguageFragment, TokenSpan


class LanguagePairAnalyzer(Protocol):
    """Structural interface for bounded pair-specific decomposition."""

    def decompose(
        self,
        token: TokenSpan,
        *,
        default_language: str,
        candidate_languages: tuple[str, ...],
        lookup: Callable[[str, str], str | None],
    ) -> Sequence[LanguageFragment] | None: ...


@dataclass(frozen=True, slots=True)
class RouteFragment:
    """Internal pair-analysis fragment before conversion to public diagnostics."""

    start: int
    end: int
    language: str
    kind: Literal["compound-root", "stem", "affix"]
    phonemes: str | None = None


_GERMAN_NATIVE_WORDS = frozenset({"gehen", "lernen", "warten", "reden", "kennen"})


def decompose_token(
    token: TokenSpan,
    *,
    default_language: str,
    candidate_languages: tuple[str, ...],
    lookup: Callable[[str, str], str | None],
) -> Sequence[LanguageFragment] | None:
    """Return a unique DE/EN decomposition based only on exact lexicon hits."""
    if default_language not in {"de-de", "en-us"} or not {
        "de-de",
        "en-us",
    }.issubset(candidate_languages):
        return None
    word = token.text
    if not word.isalpha() or len(word) > 48:
        return None
    lower = word.casefold()
    if lower in _GERMAN_NATIVE_WORDS:
        return None
    candidates: list[tuple[tuple[int, int, int], list[RouteFragment]]] = []

    for split in range(3, len(word) - 2):
        left = lower[:split]
        right = lower[split:]
        if len(right) < 3:
            continue
        if lookup("en-us", left) is not None and lookup("de-de", right) is not None:
            candidates.append(
                (
                    (len(left), len(right), 2),
                    [
                        RouteFragment(
                            token.char_start,
                            token.char_start + split,
                            "en-us",
                            "compound-root",
                        ),
                        RouteFragment(
                            token.char_start + split,
                            token.char_end,
                            "de-de",
                            "compound-root",
                        ),
                    ],
                )
            )
        if lookup("de-de", left) is not None and lookup("en-us", right) is not None:
            candidates.append(
                (
                    (len(right), len(left), 1),
                    [
                        RouteFragment(
                            token.char_start,
                            token.char_start + split,
                            "de-de",
                            "compound-root",
                        ),
                        RouteFragment(
                            token.char_start + split,
                            token.char_end,
                            "en-us",
                            "compound-root",
                        ),
                    ],
                )
            )

    morphology = _morphology_candidate(token, lower, lookup)
    if morphology is not None:
        candidates.append(((len(morphology[1]), len(morphology[2]), 3), morphology[0]))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        return None
    return tuple(
        LanguageFragment(
            fragment.start,
            fragment.end,
            word[fragment.start - token.char_start : fragment.end - token.char_start],
            fragment.language,
            "auto",
            fragment.kind,
        )
        for fragment in candidates[0][1]
    )


def _morphology_candidate(
    token: TokenSpan,
    lower: str,
    lookup: Callable[[str, str], str | None],
) -> tuple[list[RouteFragment], str, str] | None:
    if lower.startswith("ge") and lower.endswith("t") and len(lower) > 5:
        stem = lower[2:-1]
        if len(stem) >= 3 and lookup("en-us", stem) is not None:
            return (
                [
                    RouteFragment(
                        token.char_start, token.char_start + 2, "de-de", "affix"
                    ),
                    RouteFragment(
                        token.char_start + 2, token.char_end - 1, "en-us", "stem"
                    ),
                    RouteFragment(token.char_end - 1, token.char_end, "de-de", "affix"),
                ],
                stem,
                "",
            )
    if lower.endswith("en") and len(lower) > 5:
        stem = lower[:-2]
        if len(stem) >= 3 and lookup("en-us", stem) is not None:
            return (
                [
                    RouteFragment(
                        token.char_start, token.char_end - 2, "en-us", "stem"
                    ),
                    RouteFragment(token.char_end - 2, token.char_end, "de-de", "affix"),
                ],
                stem,
                "",
            )
    return None


__all__ = ["RouteFragment", "decompose_token"]
