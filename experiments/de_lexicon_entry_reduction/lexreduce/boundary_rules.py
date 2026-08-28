"""Small shared German boundary transformations admitted by diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Any


@dataclass(slots=True)
class FinalComponentStressDemotionRule:
    """Demote only the first primary stress of the final component."""

    rule_id: str = "C2"
    version: str = "2"
    stats: Any = field(default_factory=lambda: _stats())

    def applies(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> bool:
        return (
            len(components) > 1
            and bool(variants[-1])
            and any("ˈ" in value for value in variants[-1])
        )

    def compose(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> tuple[str, ...]:
        transformed = tuple(
            tuple(value.replace("ˈ", "ˌ", 1) for value in values)
            if index == len(variants) - 1
            else values
            for index, values in enumerate(variants)
        )
        return tuple("".join(parts) for parts in product(*transformed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "version": self.version,
            "usage_count": self.stats.usage_count,
            "exact_success_count": self.stats.exact_success_count,
            "mismatch_count": self.stats.mismatch_count,
        }


@dataclass(slots=True)
class BoundaryStressClassRule:
    """Demote stressed non-initial components only at a consonant boundary."""

    rule_id: str = "C3"
    version: str = "2"
    stats: Any = field(default_factory=lambda: _stats())

    def applies(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> bool:
        if len(components) < 2:
            return False
        return any("ˈ" in value for values in variants[1:] for value in values) and all(
            component[-1:].lower() not in "aeiouyäöü" for component in components[:-1]
        )

    def compose(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> tuple[str, ...]:
        transformed = tuple(
            values
            if index == 0
            else tuple(value.replace("ˈ", "ˌ", 1) for value in values)
            for index, values in enumerate(variants)
        )
        return tuple("".join(parts) for parts in product(*transformed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "version": self.version,
            "usage_count": self.stats.usage_count,
            "exact_success_count": self.stats.exact_success_count,
            "mismatch_count": self.stats.mismatch_count,
        }


def _stats() -> Any:
    # Imported lazily to keep this module usable as a rule definition module.
    from .rules import RuleStats

    return RuleStats()


def diagnostic_boundary_rules() -> tuple[object, ...]:
    """Return the bounded rule library used by the B1 stage."""
    return (FinalComponentStressDemotionRule(), BoundaryStressClassRule())
