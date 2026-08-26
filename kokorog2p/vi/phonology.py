"""Broad Northern/Hanoi Vietnamese phonology mappings.

The parser exposes orthographic structure; this module maps that structure to
stable abstract segments before any Kokoro-specific rendering occurs.
"""

from __future__ import annotations

from enum import Enum

from .syllable import VietnameseSyllable


class Phone(str, Enum):
    """Abstract segments used by the initial Northern profile."""

    B = "b"
    D = "d"
    T = "t"
    T_ASP = "tʰ"
    K = "k"
    P = "p"
    M = "m"
    N = "n"
    NY = "ɲ"
    NG = "ŋ"
    F = "f"
    V = "v"
    S = "s"
    Z = "z"
    X = "x"
    GH = "ɣ"
    H = "h"
    L = "l"
    R = "ɹ"
    J = "j"
    W = "w"
    I = "i"
    E = "e"
    OPEN_E = "ɛ"
    U_BACK_UNROUNDED = "ɯ"
    MID_BACK_UNROUNDED = "ɤ"
    A = "a"
    SHORT_A = "ɐ"
    U = "u"
    O = "o"
    OPEN_O = "ɔ"
    SCHWA = "ə"
    AFFRICATE = "ʨ"
    RETROFLEX = "ʈ"


ONSET_PHONES: dict[str, tuple[str, ...]] = {
    "b": (Phone.B.value,),
    "đ": (Phone.D.value,),
    "d": (Phone.Z.value,),
    "gi": (Phone.Z.value,),
    "g": (Phone.GH.value,),
    "gh": (Phone.GH.value,),
    "h": (Phone.H.value,),
    "k": (Phone.K.value,),
    "c": (Phone.K.value,),
    "q": (Phone.K.value,),
    "qu": (Phone.K.value, Phone.W.value),
    "m": (Phone.M.value,),
    "n": (Phone.N.value,),
    "ng": (Phone.NG.value,),
    "ngh": (Phone.NG.value,),
    "nh": (Phone.NY.value,),
    "ph": (Phone.F.value,),
    "r": (Phone.R.value,),
    "s": (Phone.S.value,),
    "x": (Phone.S.value,),
    "t": (Phone.T.value,),
    "th": (Phone.T_ASP.value,),
    "tr": (Phone.RETROFLEX.value,),
    "ch": (Phone.AFFRICATE.value,),
    "v": (Phone.V.value,),
    "l": (Phone.L.value,),
    "kh": (Phone.X.value,),
}

NUCLEUS_PHONES: dict[str, tuple[str, ...]] = {
    "a": (Phone.A.value,),
    "ă": (Phone.SHORT_A.value,),
    "â": (Phone.MID_BACK_UNROUNDED.value,),
    "e": (Phone.OPEN_E.value,),
    "ê": (Phone.E.value,),
    "i": (Phone.I.value,),
    "y": (Phone.I.value,),
    "o": (Phone.OPEN_O.value,),
    "ô": (Phone.O.value,),
    "ơ": (Phone.MID_BACK_UNROUNDED.value,),
    "u": (Phone.U.value,),
    "ư": (Phone.U_BACK_UNROUNDED.value,),
    "ia": (Phone.I.value, Phone.SCHWA.value),
    "iê": (Phone.I.value, Phone.SCHWA.value),
    "ya": (Phone.I.value, Phone.SCHWA.value),
    "yê": (Phone.I.value, Phone.SCHWA.value),
    "ua": (Phone.U.value, Phone.SCHWA.value),
    "uô": (Phone.U.value, Phone.SCHWA.value),
    "ưa": (Phone.U_BACK_UNROUNDED.value, Phone.SCHWA.value),
    "ươ": (Phone.U_BACK_UNROUNDED.value, Phone.SCHWA.value),
    "oa": (Phone.W.value, Phone.A.value),
    "oe": (Phone.W.value, Phone.OPEN_E.value),
    "uê": (Phone.W.value, Phone.E.value),
    "uy": (Phone.W.value, Phone.I.value),
    "uâ": (Phone.W.value, Phone.MID_BACK_UNROUNDED.value),
    "eo": (Phone.E.value, Phone.OPEN_O.value),
    "êu": (Phone.E.value, Phone.U.value),
    "oi": (Phone.O.value, Phone.J.value),
    "ôi": (Phone.O.value, Phone.J.value),
    "ơi": (Phone.MID_BACK_UNROUNDED.value, Phone.J.value),
    "ui": (Phone.U.value, Phone.J.value),
    "ưi": (Phone.U_BACK_UNROUNDED.value, Phone.J.value),
    "ưu": (Phone.U_BACK_UNROUNDED.value, Phone.W.value),
    "iu": (Phone.I.value, Phone.W.value),
}

CODA_PHONES: dict[str, tuple[str, ...]] = {
    "p": (Phone.P.value,),
    "t": (Phone.T.value,),
    "c": (Phone.K.value,),
    "k": (Phone.K.value,),
    "m": (Phone.M.value,),
    "n": (Phone.N.value,),
    "ng": (Phone.NG.value,),
    "nh": (Phone.NG.value,),
    "ch": (Phone.K.value,),
    "i": (Phone.J.value,),
    "y": (Phone.J.value,),
    "o": (Phone.W.value,),
    "u": (Phone.W.value,),
}
MEDIAL_PHONES: dict[str, tuple[str, ...]] = {
    "u": (Phone.W.value,),
    "o": (Phone.W.value,),
}


def map_onset(onset: str | None) -> tuple[str, ...]:
    """Map an orthographic onset to broad abstract segments."""
    return ONSET_PHONES.get(onset or "", ())


def map_medial(medial: str | None) -> tuple[str, ...]:
    """Map an orthographic medial glide to abstract segments."""
    if medial is None:
        return ()
    try:
        return MEDIAL_PHONES[medial]
    except KeyError as exc:
        raise ValueError(f"unsupported Vietnamese medial: {medial!r}") from exc


def map_nucleus(nucleus: str) -> tuple[str, ...]:
    """Map an orthographic nucleus to broad abstract segments."""
    try:
        return NUCLEUS_PHONES[nucleus]
    except KeyError as exc:
        raise ValueError(f"unsupported Vietnamese nucleus: {nucleus!r}") from exc


def map_coda(coda: str | None) -> tuple[str, ...]:
    """Map an orthographic coda or off-glide to abstract segments."""
    if coda is None:
        return ()
    try:
        return CODA_PHONES[coda]
    except KeyError as exc:
        raise ValueError(f"unsupported Vietnamese coda: {coda!r}") from exc


def syllable_to_phones(syllable: VietnameseSyllable) -> tuple[str, ...]:
    """Render a parsed syllable as abstract segment strings without tone."""
    return (
        map_onset(syllable.onset)
        + map_medial(syllable.medial)
        + map_nucleus(syllable.nucleus)
        + map_coda(syllable.coda)
    )


__all__ = [
    "CODA_PHONES",
    "NUCLEUS_PHONES",
    "ONSET_PHONES",
    "Phone",
    "map_coda",
    "map_medial",
    "map_nucleus",
    "map_onset",
    "syllable_to_phones",
]
