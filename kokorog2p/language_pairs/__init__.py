"""Language-pair analyzers used by the automatic router."""

from kokorog2p.language_pairs.de_en import (
    LanguagePairAnalyzer,
    RouteFragment,
    decompose_token,
)
from kokorog2p.language_pairs.registry import get_pair_analyzer

__all__ = [
    "LanguagePairAnalyzer",
    "RouteFragment",
    "decompose_token",
    "get_pair_analyzer",
]
