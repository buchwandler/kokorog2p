"""Declarative phonology facts for the Swedish rule-based frontend.

The constants in this module describe the clean-room runtime rule system.  No
benchmark files or other external resources are imported here.
"""

from __future__ import annotations

from typing import Final

HARD_VOWELS: Final[frozenset[str]] = frozenset("aouå")
SOFT_VOWELS: Final[frozenset[str]] = frozenset("eiyäöé")
VOWELS: Final[frozenset[str]] = HARD_VOWELS | SOFT_VOWELS
ACCEPTED_LETTERS: Final[frozenset[str]] = frozenset("abcdefghijklmnopqrstuvwxyzåäöé")

LONG_VOWELS: Final[dict[str, str]] = {
    "a": "ɑː",
    "e": "eː",
    "é": "eː",
    "i": "iː",
    "o": "uː",
    "u": "ʉː",
    "y": "yː",
    "å": "oː",
    "ä": "ɛː",
    "ö": "øː",
}

SHORT_VOWELS: Final[dict[str, str]] = {
    "a": "a",
    "e": "ɛ",
    "i": "ɪ",
    "o": "ɔ",
    "u": "ɵ",
    "y": "ʏ",
    "å": "ɔ",
    "ä": "ɛ",
    "ö": "œ",
}

SIMPLE_CONSONANTS: Final[dict[str, str]] = {
    "b": "b",
    "d": "d",
    "f": "f",
    "h": "h",
    "j": "j",
    "l": "l",
    "m": "m",
    "n": "n",
    "p": "p",
    "r": "r",
    "s": "s",
    "t": "t",
    "v": "v",
}

RETROFLEX_MAP: Final[dict[tuple[str, str], str]] = {
    ("r", "t"): "ʈ",
    ("r", "d"): "ɖ",
    ("r", "n"): "ɳ",
    ("r", "s"): "ʂ",
    ("r", "l"): "ɭ",
}

# Longest first.  The rule engine handles context-sensitive entries separately.
LONGEST_GRAPHEMES: Final[tuple[tuple[str, str, str], ...]] = (
    ("skj", "ɧ", "SV-C-001-SKJ"),
    ("stj", "ɧ", "SV-C-002-STJ"),
    ("sch", "ɧ", "SV-C-004-SCH"),
    ("sj", "ɧ", "SV-C-003-SJ"),
    ("tj", "ɕ", "SV-C-010-TJ"),
    ("kj", "ɕ", "SV-C-011-KJ"),
    ("dj", "j", "SV-C-020-DJ"),
    ("gj", "j", "SV-C-021-GJ"),
    ("hj", "j", "SV-C-022-HJ"),
    ("lj", "j", "SV-C-023-LJ"),
    ("ng", "ŋ", "SV-C-030-NG"),
    ("sk", "", "SV-C-120-SK"),
    ("ck", "k", "SV-G-001-CK"),
    ("qu", "kv", "SV-G-002-QU"),
    ("qv", "kv", "SV-G-003-QV"),
)

STRESS_NEUTRAL_SUFFIXES: Final[tuple[str, ...]] = (
    "ande",
    "ende",
    "ade",
    "ande",
    "en",
    "et",
    "er",
    "ar",
    "or",
    "na",
)

FEATURE_SUFFIXES: Final[tuple[tuple[str, str], ...]] = (
    ("tion", "suffix_tion"),
    ("sion", "suffix_sion"),
    ("itet", "suffix_itet"),
    ("era", "suffix_era"),
    ("ering", "suffix_ering"),
    ("ism", "suffix_ism"),
    ("ist", "suffix_ist"),
)

# These are source-level IPA tokens, not individual Unicode characters.
SWEDISH_KOKORO_REMAP: Final[dict[str, str]] = {
    "ɧ": "ʃ",
    "ɕ": "ʃ",
    "ʈ": "t",
    "ɖ": "d",
    "ɳ": "n",
    "ʂ": "ʃ",
    "ɭ": "l",
    "ʉː": "u",
    "ɵ": "ə",
    "ʏ": "ɪ",
    "œ": "ɔ",
    "øː": "ɔ",
    "ɑː": "ɑ",
    "eː": "ɛ",
    "iː": "i",
    "uː": "u",
    "yː": "y",
    "oː": "ɔ",
    "ɛː": "ɛ",
    "a": "ɑ",
    "e": "ɛ",
    "o": "ɔ",
    "r": "ɹ",
}

KOKORO_SUPPORTED_PHONES: Final[frozenset[str]] = frozenset(
    "AIWYbdfhijklmnpstuvwzðŋɑɔəɛɜɡɪɹʃʊʌʒʤʧˈˌθᵊ"
)
