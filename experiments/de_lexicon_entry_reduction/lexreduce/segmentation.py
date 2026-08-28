"""Compact spelling/constituent segmentation scorer."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class SegmentationScorer:
    """Fixed integer weights over bounded constituent features."""

    weights: tuple[int, ...] = (-100, -12, -4, 2, 1)
    version: str = "1"
    feature_names: tuple[str, ...] = (
        "component_count",
        "one_character_components",
        "short_components",
        "length_variance",
        "boundary_count",
    )

    def score(self, components: tuple[str, ...]) -> int:
        lengths = tuple(len(component) for component in components)
        one_character = sum(length == 1 for length in lengths)
        short = sum(length <= 2 for length in lengths)
        variance = max(lengths) - min(lengths) if lengths else 0
        values = (
            len(components),
            one_character,
            short,
            variance,
            max(0, len(components) - 1),
        )
        return sum(
            weight * value for weight, value in zip(self.weights, values, strict=True)
        )

    def key(
        self, components: tuple[str, ...]
    ) -> tuple[int, tuple[int, tuple[int, ...], tuple[str, ...]]]:
        from .composer import segmentation_rank

        return self.score(components), segmentation_rank(components)

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "feature_names": list(self.feature_names),
            "integer_weights": list(self.weights),
            "serialized_bytes": len(str(self.weights).encode()),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> SegmentationScorer:
        return cls(
            tuple(
                int(weight)
                for weight in value.get("integer_weights", (-100, -12, -4, 2, 1))
            ),
            str(value.get("version", "1")),
            tuple(str(name) for name in value.get("feature_names", ())),
        )
