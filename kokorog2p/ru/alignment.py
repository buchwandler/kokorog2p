"""Conservative alignment of sentence-level Russian stress annotations."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .accent import COMBINING_ACUTE


class RussianAlignmentError(ValueError):
    """Raised when an accentuator rewrites more than allowed stress/ё marks."""


@dataclass(frozen=True)
class TextAlignment:
    """Mapping between raw source and annotated text character boundaries."""

    source: str
    accented: str
    source_boundaries: tuple[int, ...]
    accented_boundaries: tuple[int, ...]
    adapter_name: str

    def accented_span(self, source_start: int, source_end: int) -> tuple[int, int]:
        """Return the annotated span corresponding to a source character span."""
        canonical_start = self.source_boundaries[source_start]
        canonical_end = self.source_boundaries[source_end]
        start = max(
            index
            for index, value in enumerate(self.accented_boundaries)
            if value == canonical_start
        )
        end = max(
            index
            for index, value in enumerate(self.accented_boundaries)
            if value == canonical_end
        )
        return start, end

    def accented_for_source(self, source_start: int, source_end: int) -> str:
        start, end = self.accented_span(source_start, source_end)
        return self.accented[start:end]


def _canonical_units(text: str) -> tuple[str, tuple[int, ...]]:
    units: list[str] = []
    boundaries = [0]
    for raw_char in text:
        if raw_char == "ё":
            normalized = "е"
        elif raw_char == "Ё":
            normalized = "Е"
        else:
            normalized = unicodedata.normalize("NFD", raw_char)
        for char in normalized:
            if char in {COMBINING_ACUTE, "\u0308"} and raw_char in {"ё", "Ё"}:
                continue
            if char == COMBINING_ACUTE:
                continue
            units.append(char)
        boundaries.append(len(units))
    return "".join(units), tuple(boundaries)


def align_accented_text(
    source: str,
    accented: str,
    *,
    adapter_name: str = "unknown",
) -> TextAlignment:
    """Validate and map allowed stress/ё changes back to source offsets."""
    source_canonical, source_boundaries = _canonical_units(source)
    accented_canonical, accented_boundaries = _canonical_units(accented)
    if source_canonical != accented_canonical:
        mismatch = next(
            (
                index
                for index, (left, right) in enumerate(
                    zip(source_canonical, accented_canonical, strict=False)
                )
                if left != right
            ),
            min(len(source_canonical), len(accented_canonical)),
        )
        raise RussianAlignmentError(
            f"Russian accentuation changed normal text at canonical index {mismatch}; "
            f"adapter={adapter_name!r}, source excerpt={source!r}, "
            f"processed excerpt={accented!r}"
        )
    return TextAlignment(
        source=source,
        accented=accented,
        source_boundaries=source_boundaries,
        accented_boundaries=accented_boundaries,
        adapter_name=adapter_name,
    )
