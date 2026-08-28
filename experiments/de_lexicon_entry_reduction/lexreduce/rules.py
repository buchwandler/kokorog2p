"""Global oracle-free pronunciation composition rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from itertools import product
from typing import Any, Protocol

from .selector import Candidate, RuleSelector


@dataclass(slots=True)
class RuleStats:
    usage_count: int = 0
    exact_success_count: int = 0
    mismatch_count: int = 0


class CompositionRule(Protocol):
    rule_id: str
    version: str
    stats: RuleStats

    def applies(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> bool: ...

    def compose(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> tuple[str, ...]: ...

    def as_dict(self) -> dict[str, Any]: ...


@dataclass(slots=True)
class ConcatenationRule:
    rule_id: str = "C0"
    version: str = "1"
    stats: RuleStats = field(default_factory=RuleStats)

    def applies(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> bool:
        return True

    def compose(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> tuple[str, ...]:
        return tuple("".join(parts) for parts in product(*variants))

    def as_dict(self) -> dict[str, Any]:
        return _rule_dict(self)


@dataclass(slots=True)
class CompoundStressDemotionRule:
    rule_id: str = "C1"
    version: str = "1"
    stats: RuleStats = field(default_factory=RuleStats)

    def applies(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
    ) -> bool:
        return len(components) > 1 and any(
            "ˈ" in value for values in variants[1:] for value in values
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
        return _rule_dict(self)


def _rule_dict(rule: CompositionRule) -> dict[str, Any]:
    return {
        "rule_id": rule.rule_id,
        "version": rule.version,
        "usage_count": rule.stats.usage_count,
        "exact_success_count": rule.stats.exact_success_count,
        "mismatch_count": rule.stats.mismatch_count,
    }


def rule_from_dict(value: Mapping[str, Any]) -> CompositionRule:
    rule_id = str(value["rule_id"])
    if rule_id == "C0":
        rule: CompositionRule = ConcatenationRule()
    elif rule_id == "C1":
        rule = CompoundStressDemotionRule()
    elif rule_id == "C2":
        from .boundary_rules import FinalComponentStressDemotionRule

        rule = FinalComponentStressDemotionRule()
    elif rule_id == "C3":
        from .boundary_rules import BoundaryStressClassRule

        rule = BoundaryStressClassRule()
    else:
        raise ValueError(f"unknown composition rule: {rule_id}")
    rule.version = str(value.get("version", "1"))
    rule.stats = RuleStats(
        int(value.get("usage_count", 0)),
        int(value.get("exact_success_count", 0)),
        int(value.get("mismatch_count", 0)),
    )
    return rule


@dataclass(slots=True)
class RuleSet:
    """Ordered global rules shared by the builder and runtime decoder."""

    rules: tuple[CompositionRule, ...] = field(
        default_factory=lambda: (ConcatenationRule(),)
    )
    composer_version: str = "1"

    selector: RuleSelector | None = None

    def propose(
        self,
        word: str,
        components: tuple[str, ...],
        literals: Mapping[str, tuple[str, ...]],
    ) -> tuple[Candidate, ...]:
        variants = tuple(literals[component] for component in components)
        return tuple(
            Candidate(rule.rule_id, rule.compose(word, components, variants))
            for rule in self.rules
            if rule.applies(word, components, variants)
        )

    def derive(
        self,
        word: str,
        components: tuple[str, ...],
        literals: Mapping[str, tuple[str, ...]],
    ) -> tuple[str, ...] | None:
        candidates = self.propose(word, components, literals)
        if not candidates:
            return None
        selected = (
            self.selector.choose(
                word,
                components,
                tuple(literals[component] for component in components),
                candidates,
            )
            if self.selector is not None
            else candidates[0]
        )
        if selected is None:
            return None
        for rule in self.rules:
            if rule.rule_id == selected.rule_id:
                rule.stats.usage_count += 1
                break
        return selected.pronunciation

    def record_result(self, rule_id: str | None, exact: bool) -> None:
        if rule_id is None:
            return
        for rule in self.rules:
            if rule.rule_id == rule_id:
                if exact:
                    rule.stats.exact_success_count += 1
                else:
                    rule.stats.mismatch_count += 1
                return

    def derive_with_rule(
        self,
        word: str,
        components: tuple[str, ...],
        literals: Mapping[str, tuple[str, ...]],
    ) -> tuple[str | None, tuple[str, ...] | None]:
        candidates = self.propose(word, components, literals)
        if not candidates:
            return None, None
        selected = (
            self.selector.choose(
                word,
                components,
                tuple(literals[component] for component in components),
                candidates,
            )
            if self.selector is not None
            else candidates[0]
        )
        if selected is None:
            return None, None
        for rule in self.rules:
            if rule.rule_id == selected.rule_id:
                rule.stats.usage_count += 1
                break
        return selected.rule_id, selected.pronunciation

    def as_dict(self) -> dict[str, Any]:
        return {
            "composer_version": self.composer_version,
            "rules": [rule.as_dict() for rule in self.rules],
            "selector": self.selector.as_dict() if self.selector else None,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RuleSet:
        return cls(
            tuple(rule_from_dict(item) for item in value.get("rules", [])),
            str(value.get("composer_version", "1")),
            RuleSelector.from_dict(value["selector"])
            if value.get("selector")
            else None,
        )


def default_rules(
    enable_compound_stress: bool = False,
    *,
    selector: RuleSelector | None = None,
    boundary_rules: bool = False,
) -> RuleSet:
    rules: Sequence[CompositionRule]
    if enable_compound_stress:
        rules = (CompoundStressDemotionRule(),)
        if boundary_rules:
            from .boundary_rules import diagnostic_boundary_rules

            rules = (*rules, *diagnostic_boundary_rules())
        rules = (*rules, ConcatenationRule())
    else:
        rules = (ConcatenationRule(),)
    return RuleSet(tuple(rules), selector=selector)
