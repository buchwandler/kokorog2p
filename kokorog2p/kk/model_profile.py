"""Raw eSpeak-NG to Kokoro compatibility profile for Kazakh."""

from __future__ import annotations

from dataclasses import dataclass

from kokorog2p.vocab import get_vocab, validate_for_kokoro

TARGET_MODEL = "1.0"
PROFILE_NAME = "KokoroKazakhEspeakV1"

# These are generic eSpeak tie spellings for single Kokoro labels. Ordinary
# non-English IPA symbols intentionally do not appear in this mapping.
_ESPEAK_TIED_MAP = {
    "a^ɪ": "I",
    "a^ʊ": "W",
    "d^z": "ʣ",
    "d^ʒ": "ʤ",
    "e^ɪ": "A",
    "o^ʊ": "O",
    "ə^ʊ": "Q",
    "s^s": "S",
    "t^s": "ʦ",
    "t^ʃ": "ʧ",
    "ɔ^ɪ": "Y",
    "a͡ɪ": "I",
    "a͡ʊ": "W",
    "d͡z": "ʣ",
    "d͡ʒ": "ʤ",
    "e͡ɪ": "A",
    "o͡ʊ": "O",
    "ə͡ʊ": "Q",
    "s͡s": "S",
    "t͡s": "ʦ",
    "t͡ʃ": "ʧ",
    "ɔ͡ɪ": "Y",
}


@dataclass(frozen=True)
class KazakhVocabularyError(ValueError):
    """Actionable strict-mode error for a symbol outside Kokoro's vocabulary."""

    invalid_symbol: str
    source_token: str
    raw_ipa: str
    normalized_ipa: str

    def __str__(self) -> str:
        return (
            f"Unsupported Kazakh Kokoro symbol {self.invalid_symbol!r} "
            f"(U+{ord(self.invalid_symbol):04X}) in source token "
            f"{self.source_token!r}; raw={self.raw_ipa!r}, "
            f"normalized={self.normalized_ipa!r}"
        )


def normalize_espeak_symbols(raw: str) -> str:
    """Apply only generic tied-phoneme compatibility replacements."""
    normalized = raw
    for old, new in sorted(_ESPEAK_TIED_MAP.items(), key=lambda item: -len(item[0])):
        normalized = normalized.replace(old, new)
    return normalized.replace("^", "").replace("͡", "")


def transform_kazakh_ipa(raw_ipa: str) -> str:
    """Normalize raw Kazakh eSpeak IPA for the stock Kokoro model."""
    return normalize_espeak_symbols(raw_ipa)


def validate_kazakh_symbols(
    ipa: str,
    *,
    source_token: str = "",
    raw_ipa: str = "",
    strict: bool = True,
) -> list[str]:
    """Validate final labels, raising or returning unsupported symbols."""
    valid, invalid = validate_for_kokoro(ipa, model=TARGET_MODEL)
    if valid:
        return []
    if strict:
        raise KazakhVocabularyError(invalid[0], source_token, raw_ipa, ipa)
    return invalid


def model_profile_vocab() -> dict[str, int]:
    """Return an isolated copy of the stock target mapping for diagnostics."""
    return dict(get_vocab(TARGET_MODEL))


__all__ = [
    "PROFILE_NAME",
    "TARGET_MODEL",
    "KazakhVocabularyError",
    "model_profile_vocab",
    "normalize_espeak_symbols",
    "transform_kazakh_ipa",
    "validate_kazakh_symbols",
]
