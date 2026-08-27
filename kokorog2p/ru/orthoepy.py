"""Small, independently sourced Russian orthoepy normalization layer."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .accent import COMBINING_ACUTE, RUSSIAN_VOWELS

# Avanesov and Panov describe the literary -ого/-его ending as [əvə]/[ɪvə].
# These lexical items retain /g/ in standard pronunciation and are deliberately
# kept as a small exception set rather than inferred from arbitrary substrings.
_KEEP_G_EXCEPTIONS = frozenset(
    {"много", "немного", "строго", "дорого", "итого", "убого"}
)

# The entries below are conservative dictionary-backed examples of standard
# cluster reduction. They are not a general consonant deletion rule.
_SILENT_LETTERS: dict[str, frozenset[int]] = {
    "сердце": frozenset({3}),  # д before ц
    "солнце": frozenset({2}),  # л before нц
    "праздник": frozenset({4}),  # д before н
}

# Gramota.ru and standard orthoepic descriptions list these lexicalized чн
# pronunciations with [шн]. Modern productive чн remains unchanged.
_SHN_WORDS = frozenset({"конечно", "скучно", "нарочно", "яичница"})

_WORD_RE = re.compile(r"[\wёЁ]+(?:\u0301[\wёЁ]*)?", re.UNICODE)


@dataclass(frozen=True)
class OrthoepyResult:
    source: str
    rewritten: str
    applied_rules: tuple[str, ...]


def _base_indices(word: str) -> list[int]:
    return [
        index
        for index, char in enumerate(word)
        if char in RUSSIAN_VOWELS
        or (char.isalpha() and char.lower() in "бвгджзйклмнпрстфхцчшщ")
    ]


def find_stressed_vowel_ordinal(word: str) -> int | None:
    """Return the zero-based ordinal of the vowel carrying combining acute."""
    ordinal = 0
    for index, char in enumerate(word):
        if char in RUSSIAN_VOWELS:
            if index + 1 < len(word) and word[index + 1] == COMBINING_ACUTE:
                return ordinal
            ordinal += 1
    return None


def reattach_stress_by_vowel_ordinal(word: str, ordinal: int | None) -> str:
    """Remove acute marks and attach one to the requested vowel ordinal."""
    clean = word.replace(COMBINING_ACUTE, "")
    if ordinal is None:
        return clean
    current = 0
    result: list[str] = []
    for char in clean:
        result.append(char)
        if char in RUSSIAN_VOWELS:
            if current == ordinal:
                result.append(COMBINING_ACUTE)
            current += 1
    return "".join(result)


def _word_base(word: str) -> str:
    return "".join(
        char for char in word.lower() if char in RUSSIAN_VOWELS or char.isalpha()
    )


def _replace_final_g(word: str) -> tuple[str, bool]:
    base = _word_base(word)
    if len(base) < 3 or base in _KEEP_G_EXCEPTIONS or not base.endswith(("ого", "его")):
        return word, False
    seen = 0
    target = len(base) - 2
    chars = list(word)
    for index, char in enumerate(chars):
        if char.lower() in RUSSIAN_VOWELS or char.isalpha():
            if seen == target and char.lower() == "г":
                chars[index] = "В" if char.isupper() else "в"
                return "".join(chars), True
            seen += 1
    return word, False


def _remove_silent_letter(word: str) -> tuple[str, bool]:
    base = _word_base(word)
    positions = _SILENT_LETTERS.get(base)
    if not positions:
        return word, False
    target = next(iter(positions))
    seen = 0
    chars = list(word)
    for index, char in enumerate(chars):
        if char.isalpha():
            if seen == target:
                del chars[index]
                return "".join(chars), True
            seen += 1
    return word, False


def _replace_lexical_shn(word: str) -> tuple[str, bool]:
    base = _word_base(word)
    if base not in _SHN_WORDS:
        return word, False
    for index, char in enumerate(word):
        if char.lower() == "ч":
            replacement = "Ш" if char.isupper() else "ш"
            return word[:index] + replacement + word[index + 1 :], True
    return word, False


def _rewrite_word(word: str) -> tuple[str, list[str]]:
    ordinal = find_stressed_vowel_ordinal(word)
    rules: list[str] = []
    rewritten, changed = _replace_final_g(word)
    if changed:
        rules.append("final-ogo-ego-v")
    rewritten, changed = _remove_silent_letter(rewritten)
    if changed:
        rules.append("silent-cluster")
    rewritten, changed = _replace_lexical_shn(rewritten)
    if changed:
        rules.append("lexical-chn-shn")
    if rules and ordinal is not None:
        rewritten = reattach_stress_by_vowel_ordinal(rewritten, ordinal)
    return rewritten, rules


def apply_orthoepy(accented_text: str) -> OrthoepyResult:
    """Apply conservative word-level literary pronunciation rewrites."""
    applied: list[str] = []

    def replace(match: re.Match[str]) -> str:
        rewritten, rules = _rewrite_word(match.group())
        applied.extend(rules)
        return rewritten

    rewritten = _WORD_RE.sub(replace, unicodedata.normalize("NFC", accented_text))
    return OrthoepyResult(accented_text, rewritten, tuple(applied))
