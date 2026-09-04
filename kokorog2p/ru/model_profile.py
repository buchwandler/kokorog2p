"""Pure transforms for the stock Kokoro 1.0 Russian label profile."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from kokorog2p.vocab import get_vocab, validate_for_kokoro

TARGET_MODEL = "1.0"
PROFILE_NAME = "KokoroRussianV2"

# Model compatibility substitutions for IPA symbols observed in LexHint data.
_MODEL_SYMBOL_MAP = {
    "ɫ": "l",  # hard-l allophone is represented by the ordinary lateral label.
    "ɨ": "ɪ",  # central high vowel uses the model's front reduced-vowel label.
    "ᵻ": "ɪ",  # eSpeak's internal near-high notation is not a target symbol.
    "ɤ": "ə",  # central back vowel is represented by the schwa label.
    "ɵ": "ə",  # centralized rounded vowel has no separate target ID.
    "ɒ": "ɑ",  # open back allophone folds into the target back vowel.
}

RUSSIAN_VOWELS = frozenset("aɑɐeɛiɪoɔuʊəɨɤɵɒ")
_STRESS = frozenset("ˈˌ")
_PALATAL = "ʲ"
_IPA_WORD_CHARS = (
    RUSSIAN_VOWELS
    | _STRESS
    | frozenset("bcd fghjklmnpqrstvwxyzɡʃʒʂɕɣʁʎɹɾtʃdʒʧʤʦʨŋɲːʔβθχ") - {" "}
)


@dataclass(frozen=True)
class RussianVocabularyError(ValueError):
    """Actionable strict-mode error for a symbol outside the target profile."""

    invalid_symbol: str
    source_token: str
    raw_ipa: str
    normalized_ipa: str

    def __str__(self) -> str:
        return (
            f"Unsupported Russian Kokoro symbol {self.invalid_symbol!r} "
            f"(U+{ord(self.invalid_symbol):04X}) in source token "
            f"{self.source_token!r}; raw={self.raw_ipa!r}, "
            f"normalized={self.normalized_ipa!r}"
        )


def normalize_russian_lexicon_ipa(ipa: str, *, preserve_stress: bool = True) -> str:
    """Normalize LexHint IPA into the Russian Kokoro model vocabulary."""
    normalized = unicodedata.normalize("NFC", ipa)
    normalized = "".join(_MODEL_SYMBOL_MAP.get(char, char) for char in normalized)
    normalized = re.sub(r"([bcdfghjklmnpqrstvwxyzɡʃʒʂɕɣʁʎɹɾ])ʲʲ+", r"\1ʲ", normalized)
    if not preserve_stress:
        normalized = normalized.translate({ord(char): None for char in _STRESS})
    return normalized


def normalize_espeak_symbols(raw: str) -> str:
    """Backward-compatible alias for the model symbol normalization."""
    return normalize_russian_lexicon_ipa(raw)


def _stress_vowels(word: str) -> list[tuple[int, str | None]]:
    marks: str | None = None
    vowels: list[tuple[int, str | None]] = []
    for index, char in enumerate(word):
        if char in _STRESS:
            marks = char
        elif char in RUSSIAN_VOWELS:
            vowels.append((index, marks))
            marks = None
    return vowels


def _reduce_word(word: str) -> str:
    vowels = _stress_vowels(word)
    if not vowels:
        return word
    primary_index = next(
        (index for index, (_, mark) in enumerate(vowels) if mark == "ˈ"), None
    )
    protected: set[int] = set()
    for index, (_, mark) in enumerate(vowels):
        if (
            mark == "ˈ"
            or mark == "ˌ"
            and (primary_index is None or index < primary_index)
        ):
            protected.add(index)
    replacements: dict[int, str] = {}
    for index, (char_pos, _mark) in enumerate(vowels):
        if index in protected:
            continue
        if word[char_pos] not in "aɑɐoɔɒɤɵ":
            continue
        previous = word[:char_pos].rstrip("ˈˌ")
        if previous.endswith((_PALATAL, "j")):
            replacements[char_pos] = "ɪ"
            continue
        following_stress = next((item for item in protected if item > index), None)
        if following_stress is None:
            replacements[char_pos] = "ə"
        elif following_stress == index + 1 or index == 0 and not previous:
            replacements[char_pos] = "ɐ"
        else:
            replacements[char_pos] = "ə"
    return "".join(replacements.get(index, char) for index, char in enumerate(word))


def apply_russian_vowel_reduction(ipa: str) -> str:
    """Apply the target profile's first-pretonic and remote reductions."""
    chunks: list[str] = []
    current: list[str] = []
    for char in ipa:
        if char in _IPA_WORD_CHARS:
            current.append(char)
        else:
            if current:
                chunks.append(_reduce_word("".join(current)))
                current = []
            chunks.append(char)
    if current:
        chunks.append(_reduce_word("".join(current)))
    return "".join(chunks)


def normalize_long_shcha(ipa: str) -> str:
    """Represent Russian щ as one long target fricative without duplicate length."""
    return re.sub(r"ɕ(?!ː)", "ɕː", ipa)


def validate_russian_symbols(
    ipa: str,
    *,
    source_token: str = "",
    raw_ipa: str = "",
    strict: bool = True,
) -> list[str]:
    """Validate final labels, raising or returning all invalid symbols."""
    valid, invalid = validate_for_kokoro(ipa, model=TARGET_MODEL)
    if valid:
        return []
    if strict:
        raise RussianVocabularyError(invalid[0], source_token, raw_ipa, ipa)
    return invalid


def transform_russian_ipa(raw_ipa: str, *, reduction: bool = True) -> str:
    """Run the pure Russian profile transforms in their documented order."""
    normalized = normalize_espeak_symbols(raw_ipa)
    if reduction:
        normalized = apply_russian_vowel_reduction(normalized)
    return normalize_long_shcha(normalized)


def model_profile_vocab() -> dict[str, int]:
    """Return an isolated copy of the stock target mapping for diagnostics."""
    return dict(get_vocab(TARGET_MODEL))
