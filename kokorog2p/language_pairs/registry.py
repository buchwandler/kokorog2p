"""Registry for bounded language-pair routing analyzers."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from kokorog2p.language_pairs.de_en import decompose_token
from kokorog2p.types import LanguageFragment

PairAnalyzer = Callable[..., Sequence[LanguageFragment] | None]

_ANALYZERS: dict[frozenset[str], PairAnalyzer] = {
    frozenset({"de-de", "en-us"}): decompose_token,
    frozenset({"de-de", "en-gb"}): decompose_token,
}


def get_pair_analyzer(
    default_language: str, languages: Sequence[str]
) -> PairAnalyzer | None:
    """Return the registered analyzer applicable to the requested language set."""
    available = frozenset(languages)
    candidates = [
        (pair, analyzer)
        for pair, analyzer in _ANALYZERS.items()
        if default_language in pair and pair <= available
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda item: (len(item[0]), sorted(item[0])))[1]


__all__ = ["PairAnalyzer", "get_pair_analyzer"]
