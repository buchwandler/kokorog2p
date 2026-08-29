"""Strict CMU ARPABET to Kokoro English phoneme conversion."""

from __future__ import annotations

import re

from kokorog2p.phonemes import US_VOCAB

_ARPABET = {
    "B": "b",
    "CH": "ʧ",
    "D": "d",
    "DH": "ð",
    "F": "f",
    "G": "ɡ",
    "HH": "h",
    "JH": "ʤ",
    "K": "k",
    "L": "l",
    "M": "m",
    "N": "n",
    "NG": "ŋ",
    "P": "p",
    "R": "ɹ",
    "S": "s",
    "SH": "ʃ",
    "T": "t",
    "TH": "θ",
    "V": "v",
    "W": "w",
    "Y": "j",
    "Z": "z",
    "ZH": "ʒ",
    "AA": "ɑ",
    "AE": "æ",
    "AH": "ə",
    "AO": "ɔ",
    "AW": "W",
    "AY": "I",
    "EH": "ɛ",
    "ER": "ɜɹ",
    "EY": "A",
    "IH": "ɪ",
    "IY": "i",
    "OW": "O",
    "OY": "Y",
    "UH": "ʊ",
    "UW": "u",
}
_TOKEN = re.compile(r"^(?P<symbol>[A-Z]{1,2})(?P<stress>[012]?)$")


def arpabet_to_kokoro(pronunciation: str) -> str:
    """Convert one CMUdict pronunciation, rejecting unknown symbols."""
    if not pronunciation.strip():
        raise ValueError("ARPABET pronunciation must not be empty")
    output: list[str] = []
    for token in pronunciation.split():
        match = _TOKEN.fullmatch(token)
        if match is None or match.group("symbol") not in _ARPABET:
            raise ValueError(f"unknown ARPABET symbol: {token!r}")
        symbol = match.group("symbol")
        value = _ARPABET[symbol]
        stress = match.group("stress")
        if stress == "1":
            value = "ˈ" + value
        elif stress == "2":
            value = "ˌ" + value
        output.append(value)
    result = "".join(output)
    if not all(char in US_VOCAB for char in result):
        raise ValueError(
            f"ARPABET conversion produced unsupported Kokoro phonemes: {result!r}"
        )
    return result


__all__ = ["arpabet_to_kokoro"]
