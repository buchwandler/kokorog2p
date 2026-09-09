"""Bounded German and English compound and morphology analysis."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from kokorog2p.lexicons.evidence import LexiconEvidence
from kokorog2p.types import LanguageFragment, TokenSpan


class LanguagePairAnalyzer(Protocol):
    """Structural interface for bounded pair-specific decomposition."""

    def decompose(
        self,
        token: TokenSpan,
        *,
        default_language: str,
        candidate_languages: tuple[str, ...],
        evidence: Callable[[str, str], LexiconEvidence | None],
    ) -> Sequence[LanguageFragment] | None: ...


@dataclass(frozen=True, slots=True)
class RouteFragment:
    """Internal pair-analysis fragment before conversion to public diagnostics."""

    start: int
    end: int
    language: str
    kind: Literal["compound-root", "stem", "affix"]
    evidence: LexiconEvidence | None = None
    phonemes: str | None = None


def _evidence_languages(evidence: LexiconEvidence | None) -> frozenset[str]:
    """Return base languages from structured pronunciation marker evidence."""
    if evidence is None or evidence.metadata is None:
        return frozenset()
    markers = evidence.metadata.get("pronunciation_language_markers", ())
    if not isinstance(markers, Sequence) or isinstance(markers, (str, bytes)):
        return frozenset()
    languages: set[str] = set()
    for marker in markers:
        if not isinstance(marker, Mapping):
            continue
        language = marker.get("language")
        if isinstance(language, str) and language:
            languages.add(language.casefold().replace("_", "-").split("-", 1)[0])
    return frozenset(languages)


def decompose_token(
    token: TokenSpan,
    *,
    default_language: str,
    candidate_languages: tuple[str, ...],
    evidence: Callable[[str, str], LexiconEvidence | None],
) -> Sequence[LanguageFragment] | None:
    """Return a bounded DE/EN decomposition from lexical evidence."""
    if (
        default_language not in {"de-de", "en-us", "en-gb"}
        or "de-de" not in candidate_languages
    ):
        return None
    english_languages = tuple(
        language for language in candidate_languages if language in {"en-us", "en-gb"}
    )
    if len(english_languages) != 1:
        return None
    english_language = english_languages[0]
    word = token.text
    if not word.isalpha() or len(word) > 48:
        return None
    lower = word.casefold()
    whole_default = evidence(default_language, lower)
    if whole_default is not None:
        if default_language != "de-de":
            return None
        if "en" in _evidence_languages(whole_default):
            english_whole = evidence(english_language, lower)
            if english_whole is not None:
                return (
                    LanguageFragment(
                        char_start=token.char_start,
                        char_end=token.char_end,
                        text=word,
                        language=english_language,
                        source="auto",
                        kind="whole-token",
                        evidence_lexicon_id=english_whole.lexicon_id,
                        evidence_kind=english_whole.kind,
                        evidence_rating=english_whole.rating,
                    ),
                )
        morphology = _morphology_candidate(
            token,
            lower,
            english_language,
            evidence,
            default_language=default_language,
            whole_default_evidence=whole_default,
        )
        if morphology is None:
            return None
        return _fragments_from_route(token, word, morphology[0])

    morphology = _morphology_candidate(
        token,
        lower,
        english_language,
        evidence,
        default_language=default_language,
        whole_default_evidence=None,
    )
    best_score: tuple[int, int, int] | None = None
    best_route: list[RouteFragment] | None = None
    ambiguous = False
    if morphology is not None:
        best_score = (len(morphology[1]), len(morphology[2]), 3)
        best_route = morphology[0]

    hypotheses = [
        ((split, len(word) - split, 2), split, True)
        for split in range(3, len(word) - 2)
    ]
    hypotheses.extend(
        (
            (len(word) - split, split, 1),
            split,
            False,
        )
        for split in range(3, len(word) - 2)
    )
    hypotheses.sort(key=lambda item: item[0], reverse=True)

    for score, split, english_left in hypotheses:
        if best_score is not None and score < best_score:
            break
        left = lower[:split]
        right = lower[split:]
        if english_left:
            left_evidence = evidence(english_language, left)
            right_evidence = evidence("de-de", right)
            languages = (english_language, "de-de")
        else:
            left_evidence = evidence("de-de", left)
            right_evidence = evidence(english_language, right)
            languages = ("de-de", english_language)
        if left_evidence is None or right_evidence is None:
            continue
        candidate = [
            RouteFragment(
                token.char_start,
                token.char_start + split,
                languages[0],
                "compound-root",
                left_evidence,
            ),
            RouteFragment(
                token.char_start + split,
                token.char_end,
                languages[1],
                "compound-root",
                right_evidence,
            ),
        ]
        if best_score is None or score > best_score:
            best_score = score
            best_route = candidate
            ambiguous = False
        elif score == best_score and candidate != best_route:
            ambiguous = True

    if ambiguous or best_route is None:
        return None
    return _fragments_from_route(token, word, best_route)


def _fragments_from_route(
    token: TokenSpan, word: str, fragments: Sequence[RouteFragment]
) -> tuple[LanguageFragment, ...]:
    return tuple(
        LanguageFragment(
            char_start=fragment.start,
            char_end=fragment.end,
            text=word[
                fragment.start - token.char_start : fragment.end - token.char_start
            ],
            language=fragment.language,
            source="auto",
            kind=fragment.kind,
            evidence_lexicon_id=(
                None if fragment.evidence is None else fragment.evidence.lexicon_id
            ),
            evidence_kind=(
                None if fragment.evidence is None else fragment.evidence.kind
            ),
            evidence_rating=(
                None if fragment.evidence is None else fragment.evidence.rating
            ),
            phonemes=fragment.phonemes,
        )
        for fragment in fragments
    )


def _morphology_candidate(
    token: TokenSpan,
    lower: str,
    english_language: str,
    evidence: Callable[[str, str], LexiconEvidence | None],
    *,
    default_language: str,
    whole_default_evidence: LexiconEvidence | None,
) -> tuple[list[RouteFragment], str, str] | None:
    """Return a bounded English stem plus German affix candidate."""
    collision = whole_default_evidence is not None
    if lower.startswith("ge") and lower.endswith("t") and len(lower) > 7:
        stem = lower[2:-1]
        if len(stem) >= 5:
            english_stem = evidence(english_language, stem)
            german_stem = evidence(default_language, stem)
            if english_stem is not None and (
                not collision or "en" in _evidence_languages(german_stem)
            ):
                return (
                    [
                        RouteFragment(
                            token.char_start,
                            token.char_start + 2,
                            default_language,
                            "affix",
                            phonemes="ɡə",
                        ),
                        RouteFragment(
                            token.char_start + 2,
                            token.char_end - 1,
                            english_language,
                            "stem",
                            english_stem,
                        ),
                        RouteFragment(
                            token.char_end - 1,
                            token.char_end,
                            default_language,
                            "affix",
                            phonemes="t",
                        ),
                    ],
                    stem,
                    "",
                )
    if lower.endswith("en") and len(lower) > 7:
        stem = lower[:-2]
        if len(stem) >= 5:
            english_stem = evidence(english_language, stem)
            german_stem = evidence(default_language, stem)
            marker_backed = whole_default_evidence is not None and (
                "en" in _evidence_languages(whole_default_evidence)
                or "en" in _evidence_languages(german_stem)
            )
            if english_stem is not None and (not collision or marker_backed):
                return (
                    [
                        RouteFragment(
                            token.char_start,
                            token.char_end - 2,
                            english_language,
                            "stem",
                            english_stem,
                        ),
                        RouteFragment(
                            token.char_end - 2,
                            token.char_end,
                            default_language,
                            "affix",
                            phonemes="ən",
                        ),
                    ],
                    stem,
                    "",
                )
    return None


__all__ = ["RouteFragment", "decompose_token"]
