"""Bounded shared affix/morpheme grammar for optional V2 experiments."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Affix:
    spelling: str
    position: str
    pronunciation: tuple[str, ...] = ("",)

    def as_dict(self) -> dict[str, Any]:
        return {
            "spelling": self.spelling,
            "position": self.position,
            "pronunciation": list(self.pronunciation),
        }


@dataclass(frozen=True, slots=True)
class AffixCandidate:
    stem: str
    prefix: Affix | None = None
    suffix: Affix | None = None

    @property
    def components(self) -> tuple[str, ...]:
        values: list[str] = []
        if self.prefix:
            values.append(self.prefix.spelling)
        values.append(self.stem)
        if self.suffix:
            values.append(self.suffix.spelling)
        return tuple(values)


@dataclass(frozen=True, slots=True)
class AffixTable:
    affixes: tuple[Affix, ...]
    max_candidates: int = 64

    def candidates(
        self, word: str, literals: Mapping[str, object]
    ) -> tuple[AffixCandidate, ...]:
        prefixes = tuple(affix for affix in self.affixes if affix.position == "prefix")
        suffixes = tuple(affix for affix in self.affixes if affix.position == "suffix")
        found: list[AffixCandidate] = []
        for affix in prefixes:
            if (
                word.startswith(affix.spelling)
                and word[len(affix.spelling) :] in literals
            ):
                found.append(AffixCandidate(word[len(affix.spelling) :], prefix=affix))
        for affix in suffixes:
            if (
                word.endswith(affix.spelling)
                and word[: -len(affix.spelling)] in literals
            ):
                found.append(AffixCandidate(word[: -len(affix.spelling)], suffix=affix))
        found.sort(key=lambda item: (len(item.components), item.components))
        return tuple(found[: self.max_candidates])

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": "1",
            "max_candidates": self.max_candidates,
            "affixes": [affix.as_dict() for affix in self.affixes],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> AffixTable:
        return cls(
            tuple(
                Affix(
                    str(item["spelling"]),
                    str(item["position"]),
                    tuple(item.get("pronunciation", [""])),
                )
                for item in value.get("affixes", ())
            ),
            int(value.get("max_candidates", 64)),
        )


def german_affix_table(*, max_candidates: int = 64) -> AffixTable:
    return AffixTable(
        tuple(Affix(value, "prefix") for value in ("un", "ver", "be", "ge"))
        + tuple(
            Affix(value, "suffix")
            for value in ("lich", "keit", "heit", "ung", "en", "er")
        ),
        max_candidates=max_candidates,
    )
