"""Compact oracle-free selectors for competing composition candidates."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Candidate:
    """A produced pronunciation candidate, with no expected-IPA field."""

    rule_id: str
    pronunciation: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompositionFeatures:
    component_count: int
    component_lengths: tuple[int, ...]
    spelling_left: str
    spelling_right: str
    capitalization: str
    stress_counts: tuple[int, ...]
    stress_positions: tuple[tuple[int, ...], ...]
    phoneme_left: str
    phoneme_right: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "component_count": self.component_count,
            "component_lengths": list(self.component_lengths),
            "spelling_left": self.spelling_left,
            "spelling_right": self.spelling_right,
            "capitalization": self.capitalization,
            "stress_counts": list(self.stress_counts),
            "stress_positions": [list(value) for value in self.stress_positions],
            "phoneme_left": self.phoneme_left,
            "phoneme_right": self.phoneme_right,
        }


def _grapheme_class(value: str) -> str:
    if not value:
        return "empty"
    if value[0].isupper():
        return "upper"
    if value[0].islower():
        return "lower"
    if value[0].isdigit():
        return "digit"
    return "other"


def _phoneme_class(value: str) -> str:
    if not value:
        return "empty"
    symbol = value[-1]
    if symbol in "aeiouyäöüɑɛɪɔʊə":
        return "vowel"
    if symbol in "ˈˌ":
        return "stress"
    return "other"


def extract_features(
    word: str,
    components: tuple[str, ...],
    variants: tuple[tuple[str, ...], ...],
) -> CompositionFeatures:
    """Extract bounded spelling and constituent features, never word identity."""
    stress_positions = tuple(
        tuple(index for index, symbol in enumerate(value) if symbol in "ˈˌ")
        for values in variants
        for value in (values[0] if values else "",)
    )
    stress_counts = tuple(
        sum(value.count("ˈ") + value.count("ˌ") for value in values)
        for values in variants
    )
    first = components[0] if components else ""
    last = components[-1] if components else ""
    first_value = variants[0][0] if variants and variants[0] else ""
    last_value = variants[-1][0] if variants and variants[-1] else ""
    if word and word.isupper():
        capitalization = "upper"
    elif word and word[:1].isupper():
        capitalization = "initial-upper"
    elif word and word.islower():
        capitalization = "lower"
    else:
        capitalization = "mixed"
    return CompositionFeatures(
        len(components),
        tuple(len(value) for value in components),
        _grapheme_class(first[-1:] if first else ""),
        _grapheme_class(last[:1] if last else ""),
        capitalization,
        stress_counts,
        stress_positions,
        _phoneme_class(first_value),
        _phoneme_class(last_value),
    )


@dataclass(frozen=True, slots=True)
class SelectorPredicate:
    feature: str
    value: str
    rule_id: str
    support: int = 0

    def matches(self, features: CompositionFeatures) -> bool:
        actual = getattr(features, self.feature)
        return _stable_value(actual) == self.value

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature": self.feature,
            "value": self.value,
            "rule_id": self.rule_id,
            "support": self.support,
        }


@dataclass(frozen=True, slots=True)
class RuleSelector:
    """A bounded ordered predicate list shared by every generated word."""

    predicates: tuple[SelectorPredicate, ...] = ()
    default_rule: str = "C0"
    version: str = "2"
    max_depth: int = 6
    max_leaves: int = 64
    min_support: int = 100
    max_serialized_bytes: int = 32 * 1024

    def select(
        self,
        features: CompositionFeatures,
        candidates: Sequence[Candidate],
    ) -> Candidate | None:
        by_rule = {candidate.rule_id: candidate for candidate in candidates}
        for predicate in self.predicates:
            if predicate.matches(features) and predicate.rule_id in by_rule:
                return by_rule[predicate.rule_id]
        return by_rule.get(self.default_rule) or (candidates[0] if candidates else None)

    def choose(
        self,
        word: str,
        components: tuple[str, ...],
        variants: tuple[tuple[str, ...], ...],
        candidates: Sequence[Candidate],
    ) -> Candidate | None:
        return self.select(extract_features(word, components, variants), candidates)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "default_rule": self.default_rule,
            "max_depth": self.max_depth,
            "max_leaves": self.max_leaves,
            "min_support": self.min_support,
            "max_serialized_bytes": self.max_serialized_bytes,
            "predicates": [predicate.as_dict() for predicate in self.predicates],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> RuleSelector:
        predicates = tuple(
            SelectorPredicate(
                str(item["feature"]),
                str(item["value"]),
                str(item["rule_id"]),
                int(item.get("support", 0)),
            )
            for item in value.get("predicates", ())
        )
        selector = cls(
            predicates,
            str(value.get("default_rule", "C0")),
            str(value.get("version", "2")),
            int(value.get("max_depth", 6)),
            int(value.get("max_leaves", 64)),
            int(value.get("min_support", 100)),
            int(value.get("max_serialized_bytes", 32 * 1024)),
        )
        if len(selector.predicates) > selector.max_leaves:
            raise ValueError("selector exceeds maximum leaves")
        return selector

    @property
    def serialized_bytes(self) -> int:
        import json

        return len(
            json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":")).encode()
        )


def _stable_value(value: object) -> str:
    if isinstance(value, tuple):
        return "(" + ",".join(_stable_value(item) for item in value) + ")"
    return str(value)


def train_selector(
    rows: Iterable[Mapping[str, Any]],
    *,
    default_rule: str = "C0",
    min_support: int = 100,
    max_leaves: int = 64,
) -> RuleSelector:
    """Fit bounded feature predicates from offline labels.

    Rows must provide ``features`` and an offline ``target_rule``. The target is
    intentionally not part of the returned runtime representation.
    """
    values: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    for row in rows:
        target = str(row["target_rule"])
        features = row["features"]
        if isinstance(features, CompositionFeatures):
            feature_dict = features.as_dict()
        else:
            feature_dict = dict(features)
        for feature, value in sorted(feature_dict.items()):
            values[(feature, _stable_value(value))][target] += 1
    predicates: list[SelectorPredicate] = []
    for (feature, value), counts in sorted(values.items()):
        target, support = max(counts.items(), key=lambda item: (item[1], item[0]))
        total = sum(counts.values())
        if support >= min_support and support == total:
            predicates.append(SelectorPredicate(feature, value, target, support))
    predicates.sort(
        key=lambda item: (-item.support, item.feature, item.value, item.rule_id)
    )
    return RuleSelector(
        tuple(predicates[:max_leaves]),
        default_rule,
        min_support=min_support,
        max_leaves=max_leaves,
    )
