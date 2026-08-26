"""Pure cleanup and validation for the Nabra Arabic phoneme profile."""

from __future__ import annotations

import re

from kokorog2p.vocab import phonemes_to_ids, validate_for_kokoro

TARGET_MODEL = "nabra-82m-v0.1"
PROFILE_NAME = "NabraMSA"

_ARTICULATION_MARKS = frozenset({"\u032a", "ˤ"})
_TIE_BARS = frozenset({"͡", "͜"})
_GROUPING_DELIMITERS = str.maketrans({"[": None, "]": None, "{": None, "}": None})
_INTERNAL_DOT_RE = re.compile(r"(?<=\S)\.(?=\S)")


def strip_espeak_articulation_marks(text: str) -> str:
    """Remove eSpeak articulation marks not represented by Nabra."""
    return "".join(char for char in text if char not in _ARTICULATION_MARKS)


def strip_tie_bars(text: str) -> str:
    """Remove combining tie bars from eSpeak affricates."""
    return "".join(char for char in text if char not in _TIE_BARS)

def strip_internal_syllable_dots(text: str) -> str:
    """Remove dots between adjacent phoneme characters, preserving final dots."""
    return _INTERNAL_DOT_RE.sub("", text)


def strip_grouping_delimiters(text: str) -> str:
    """Remove eSpeak grouping delimiters from a raw phoneme stream."""
    return text.translate(_GROUPING_DELIMITERS)


def clean_espeak_output(text: str) -> str:
    """Apply the narrow cleanup policy used by the Nabra Arabic frontend."""
    cleaned = strip_espeak_articulation_marks(text)
    cleaned = strip_tie_bars(cleaned)
    cleaned = strip_internal_syllable_dots(cleaned)
    cleaned = strip_grouping_delimiters(cleaned)
    return " ".join(cleaned.split())


def validate_nabra_symbols(text: str) -> tuple[bool, list[str]]:
    """Return whether *text* is representable by the Nabra vocabulary."""
    return validate_for_kokoro(text, model=TARGET_MODEL)


def encode_output(text: str) -> list[int]:
    """Encode validated Nabra phonemes, raising for unsupported symbols."""
    valid, invalid = validate_nabra_symbols(text)
    if not valid:
        symbols = "".join(sorted(set(invalid)))
        raise ValueError(
            "Nabra Arabic frontend produced phoneme symbols not present in the "
            f"selected target profile: {symbols}"
        )
    return phonemes_to_ids(text, model=TARGET_MODEL)


__all__ = [
    "PROFILE_NAME",
    "TARGET_MODEL",
    "clean_espeak_output",
    "encode_output",
    "strip_espeak_articulation_marks",
    "strip_tie_bars",
    "strip_grouping_delimiters",
    "strip_internal_syllable_dots",
    "validate_nabra_symbols",
]
