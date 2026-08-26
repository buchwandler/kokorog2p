"""Structural parsing for one Vietnamese orthographic syllable."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .unicode import (
    InvalidVietnameseSyllable,
    VietnameseG2PError,
    extract_tone,
    normalize_vietnamese,
)


class VietnameseTone(str, Enum):
    """The six lexical tones used by the Northern profile."""

    NGANG = "ngang"
    HUYEN = "huyen"
    HOI = "hoi"
    NGA = "nga"
    SAC = "sac"
    NANG = "nang"


@dataclass(frozen=True)
class VietnameseSyllable:
    """A parsed Vietnamese syllable independent of model rendering."""

    source: str
    onset: str | None
    medial: str | None
    nucleus: str
    coda: str | None
    tone: VietnameseTone

    @property
    def rime(self) -> str:
        """Return the parsed orthographic rime."""
        return (self.medial or "") + self.nucleus + (self.coda or "")


# Longest spellings are always considered first. ``gi`` is handled specially
# because ``gi`` can also be the onset g followed by nucleus i.
ONSET_SPELLINGS = (
    "ngh",
    "ng",
    "gh",
    "gi",
    "kh",
    "nh",
    "ph",
    "th",
    "tr",
    "ch",
    "qu",
    "b",
    "c",
    "d",
    "đ",
    "g",
    "h",
    "k",
    "l",
    "m",
    "n",
    "p",
    "q",
    "r",
    "s",
    "t",
    "v",
    "x",
)
CODA_SPELLINGS = ("ch", "nh", "ng", "p", "t", "c", "k", "m", "n")

# Nuclei are kept as orthographic identities. The phonology module owns their
# broad phonetic realization.
NUCLEI = frozenset(
    {
        "a",
        "ă",
        "â",
        "e",
        "ê",
        "i",
        "o",
        "ô",
        "ơ",
        "u",
        "ư",
        "y",
        "ia",
        "iê",
        "ya",
        "yê",
        "ua",
        "uô",
        "ưa",
        "ươ",
        "oa",
        "oe",
        "uê",
        "uy",
        "uâ",
        "eo",
        "êu",
        "oi",
        "ôi",
        "ơi",
        "ui",
        "ưi",
        "ưu",
        "iu",
    }
)
MEDIAL_NUCLEI = {
    "uyê": ("u", "yê", None),
    "uya": ("u", "ya", None),
    "uê": ("u", "ê", None),
    "uâ": ("u", "â", None),
    "oa": ("o", "a", None),
    "oă": ("o", "ă", None),
    "oe": ("o", "e", None),
}


def _select_onset(text: str) -> tuple[str | None, str]:
    for candidate in ONSET_SPELLINGS:
        if not text.startswith(candidate):
            continue
        remainder = text[len(candidate) :]
        if not remainder:
            continue
        if candidate == "gi" and remainder.startswith("i"):
            continue
        if candidate == "q":
            continue
        return candidate, remainder
    return None, text


def _parse_rime(text: str) -> tuple[str | None, str, str | None] | None:
    if not text:
        return None

    for spelling, shape in sorted(
        MEDIAL_NUCLEI.items(), key=lambda item: -len(item[0])
    ):
        if text == spelling:
            return shape

    if text in NUCLEI:
        return None, text, None

    # Final i/y and o/u are off-glides. Require a complete nucleus before them
    # so arbitrary consonant strings cannot become Vietnamese by accident.
    if len(text) > 1 and text[-1] in "iyou":
        base = text[:-1]
        parsed = _parse_rime(base)
        if parsed is not None:
            return parsed[0], parsed[1], text[-1]

    for spelling in sorted(NUCLEI, key=len, reverse=True):
        if text == spelling:
            return None, spelling, None
    return None


def _validate_spelling(onset: str | None, rime: str) -> None:
    if onset == "q":
        raise InvalidVietnameseSyllable("q must be part of the qu onset")
    first = rime[0] if rime else ""
    if onset == "c" and first not in "aăâouôơư":
        raise InvalidVietnameseSyllable("c is not legal before this Vietnamese vowel")
    if onset == "k" and first not in "eêiy":
        raise InvalidVietnameseSyllable("k is not legal before this Vietnamese vowel")
    if onset == "gh" and first not in "eêi":
        raise InvalidVietnameseSyllable("gh is only legal before e, ê, or i")
    if onset == "ngh" and first not in "eêi":
        raise InvalidVietnameseSyllable("ngh is only legal before e, ê, or i")
    if onset == "g" and first in "eê":
        raise InvalidVietnameseSyllable("g is written gh before e or ê")
    if onset == "g" and first == "i" and rime != "i":
        raise InvalidVietnameseSyllable("g is written gi before a non-i rhyme")
    if onset == "ng" and first in "eêi":
        raise InvalidVietnameseSyllable("ng is written ngh before e, ê, or i")
    if onset == "qu" and not first:
        raise InvalidVietnameseSyllable("qu requires a following nucleus")


def parse_syllable(text: str, *, strict: bool = True) -> VietnameseSyllable | None:
    """Parse one Vietnamese syllable into onset, rime, coda, and tone."""
    try:
        if not isinstance(text, str):
            raise TypeError(
                f"Vietnamese syllable must be str, got {type(text).__name__}"
            )
        if not text or any(char.isspace() for char in text):
            raise InvalidVietnameseSyllable(
                "expected exactly one non-whitespace syllable"
            )
        extraction = extract_tone(text)
        normalized = normalize_vietnamese(extraction.normalized).casefold()
        if not normalized or not all(char.isalpha() for char in normalized):
            raise InvalidVietnameseSyllable(f"invalid Vietnamese orthography: {text!r}")

        onset, rime = _select_onset(normalized)
        if onset == "qu" or onset == "gi" and rime:
            _validate_spelling(onset, rime)

        coda: str | None = None
        rime_without_coda = rime
        for candidate in CODA_SPELLINGS:
            if not rime.endswith(candidate) or len(rime) == len(candidate):
                continue
            candidate_rime = rime[: -len(candidate)]
            if _parse_rime(candidate_rime) is not None:
                coda = candidate
                rime_without_coda = candidate_rime
                break

        parsed = _parse_rime(rime_without_coda)
        if parsed is None:
            raise InvalidVietnameseSyllable(f"unsupported Vietnamese rime: {rime!r}")
        medial, nucleus, offglide = parsed
        if offglide is not None:
            if coda is not None:
                raise InvalidVietnameseSyllable("a syllable cannot have two codas")
            coda = offglide

        _validate_spelling(onset, rime_without_coda)
        tone = VietnameseTone(extraction.tone_name)
        if coda in {"p", "t", "c", "k", "ch"} and tone not in {
            VietnameseTone.NGANG,
            VietnameseTone.SAC,
            VietnameseTone.NANG,
        }:
            raise InvalidVietnameseSyllable(
                f"tone {tone.value} is not legal on checked coda {coda!r}"
            )
        return VietnameseSyllable(text, onset, medial, nucleus, coda, tone)
    except (InvalidVietnameseSyllable, TypeError):
        if strict:
            raise
        return None


def try_parse_syllable(text: str) -> VietnameseSyllable | None:
    """Return a parsed syllable or ``None`` for invalid orthography."""
    return parse_syllable(text, strict=False)


def is_vietnamese_syllable(text: str) -> bool:
    """Return true only when *text* passes structural and tone validation."""
    return try_parse_syllable(text) is not None


__all__ = [
    "CODA_SPELLINGS",
    "NUCLEI",
    "ONSET_SPELLINGS",
    "InvalidVietnameseSyllable",
    "VietnameseG2PError",
    "VietnameseSyllable",
    "VietnameseTone",
    "is_vietnamese_syllable",
    "parse_syllable",
    "try_parse_syllable",
]
