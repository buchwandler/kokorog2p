"""Language-pair analyzers used by the automatic router."""

from kokorog2p.language_pairs.de_en import (
    LanguagePairAnalyzer,
    RouteFragment,
    decompose_token,
)

__all__ = ["LanguagePairAnalyzer", "RouteFragment", "decompose_token"]
