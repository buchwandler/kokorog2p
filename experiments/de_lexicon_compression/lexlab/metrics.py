"""Small benchmark metrics shared by experiment scripts."""

from __future__ import annotations

from collections.abc import Sequence


def levenshtein(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, char in enumerate(left, 1):
        current = [i]
        for j, other in enumerate(right, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (char != other))
            )
        previous = current
    return previous[-1]


def cer(expected: Sequence[str], actual: Sequence[str]) -> float:
    reference = sum(len(value) for value in expected)
    distance = sum(
        levenshtein(left, right) for left, right in zip(expected, actual, strict=False)
    )
    distance += sum(len(value) for value in expected[len(actual) :])
    distance += sum(len(value) for value in actual[len(expected) :])
    return distance / reference if reference else (0.0 if distance == 0 else 1.0)
