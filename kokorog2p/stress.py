"""Relative stress processing for resolved phoneme strings."""

from collections.abc import Set as AbstractSet
from typing import Literal, TypeAlias

StressLevel: TypeAlias = Literal[-2, -1, 1, 2]
PRIMARY_STRESS = "ˈ"
SECONDARY_STRESS = "ˌ"
STRESSES = frozenset((PRIMARY_STRESS, SECONDARY_STRESS))


class InvalidStressLevel(ValueError):
    """Raised when a public stress override is not supported."""


def parse_stress_level(value: str | float | None) -> float | None:
    """Parse one of the supported public stress override values.

    The public string representation is deliberately exact. Numeric values are
    accepted for callers that construct overrides programmatically, but only
    the four supported levels are valid.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise InvalidStressLevel(
            f"invalid stress level {value!r}; expected -2, -1, +1, or +2"
        )
    if isinstance(value, str):
        levels = {"-2": -2.0, "-1": -1.0, "+1": 1.0, "+2": 2.0}
        if value in levels:
            return levels[value]
    elif isinstance(value, (int, float)) and value in (-2, -1, 1, 2):
        return float(value)
    raise InvalidStressLevel(
        f"invalid stress level {value!r}; expected -2, -1, +1, or +2"
    )


def apply_stress(
    phonemes: str | None,
    stress: float | None,
    *,
    vowels: AbstractSet[str],
) -> str | None:
    """Apply relative stress to a phoneme string.

    ``stress`` retains the historical numeric state-machine behavior used by
    the English lexicon. Public span values should be parsed with
    :func:`parse_stress_level` before calling this function.
    """
    if phonemes is None or stress is None:
        return phonemes

    def restress(value: str) -> str:
        """Move stress markers immediately before their associated vowel."""
        indexed = list(enumerate(value))
        stress_positions: dict[int, int] = {}
        for marker_index, phoneme in indexed:
            if phoneme not in STRESSES:
                continue
            for vowel_index, vowel in indexed[marker_index:]:
                if vowel in vowels:
                    stress_positions[marker_index] = vowel_index
                    break
        for marker_index, vowel_index in stress_positions.items():
            _, marker = indexed[marker_index]
            indexed[marker_index] = (vowel_index - 0.5, marker)
        return "".join(phoneme for _, phoneme in sorted(indexed))

    if stress < -1:
        return phonemes.replace(PRIMARY_STRESS, "").replace(SECONDARY_STRESS, "")
    if stress == -1 or (stress in (0, -0.5) and PRIMARY_STRESS in phonemes):
        return phonemes.replace(SECONDARY_STRESS, "").replace(
            PRIMARY_STRESS, SECONDARY_STRESS
        )
    if stress in (0, 0.5, 1) and all(marker not in phonemes for marker in STRESSES):
        if all(vowel not in phonemes for vowel in vowels):
            return phonemes
        return restress(SECONDARY_STRESS + phonemes)
    if stress >= 1 and PRIMARY_STRESS not in phonemes and SECONDARY_STRESS in phonemes:
        return phonemes.replace(SECONDARY_STRESS, PRIMARY_STRESS)
    if stress > 1 and all(marker not in phonemes for marker in STRESSES):
        if all(vowel not in phonemes for vowel in vowels):
            return phonemes
        return restress(PRIMARY_STRESS + phonemes)
    return phonemes


__all__ = [
    "PRIMARY_STRESS",
    "SECONDARY_STRESS",
    "STRESSES",
    "InvalidStressLevel",
    "StressLevel",
    "apply_stress",
    "parse_stress_level",
]
