"""Runtime and builder primitives for implicit lexicon entries."""

from .composer import (
    DerivationResult,
    ImplicitComposer,
    SearchLimitError,
    best_segmentation,
    top_k_segmentations,
    best_two_part_segmentation,
)
from .selector import (
    Candidate,
    CompositionFeatures,
    RuleSelector,
    extract_features,
    train_selector,
)
from .linkers import Linker, LinkerCandidate, LinkerTable, german_linker_table
from .resolver import ComponentResolver, ResolveContext
from .segmentation import SegmentationScorer
from .affixes import Affix, AffixCandidate, AffixTable, german_affix_table
from .audit import audit_runtime_representation
from .builder import BuildResult, build_implicit_lexicon
from .membership import MembershipIndex
from .optimizer import OptimizationResult, optimize_basis
from .literals import LiteralLexicon
from .prefix_index import LiteralPrefixIndex, MutableLiteralPrefixIndex
from .rules import (
    CompoundStressDemotionRule,
    ConcatenationRule,
    RuleSet,
    default_rules,
)

__all__ = [
    "Affix",
    "AffixCandidate",
    "AffixTable",
    "BuildResult",
    "Candidate",
    "ComponentResolver",
    "CompositionFeatures",
    "CompoundStressDemotionRule",
    "ConcatenationRule",
    "DerivationResult",
    "ImplicitComposer",
    "Linker",
    "LinkerCandidate",
    "LinkerTable",
    "LiteralLexicon",
    "LiteralPrefixIndex",
    "MembershipIndex",
    "MutableLiteralPrefixIndex",
    "OptimizationResult",
    "ResolveContext",
    "RuleSelector",
    "RuleSet",
    "SearchLimitError",
    "SegmentationScorer",
    "audit_runtime_representation",
    "best_segmentation",
    "best_two_part_segmentation",
    "build_implicit_lexicon",
    "default_rules",
    "extract_features",
    "german_affix_table",
    "german_linker_table",
    "optimize_basis",
    "top_k_segmentations",
    "train_selector",
]
