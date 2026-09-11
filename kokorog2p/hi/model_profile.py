"""Raw eSpeak-NG to Kokoro compatibility profile for Hindi."""

from __future__ import annotations

from dataclasses import dataclass

from kokorog2p.phonemes import strip_espeak_language_markers
from kokorog2p.vocab import get_vocab, validate_for_kokoro

TARGET_MODEL = "1.0"
PROFILE_NAME = "KokoroHindiEspeakV1"


@dataclass(frozen=True)
class HindiVocabularyError(ValueError):
    """Actionable strict-mode error for a symbol outside Kokoro's vocabulary."""

    invalid_symbol: str
    source_token: str
    raw_ipa: str
    normalized_ipa: str

    def __str__(self) -> str:
        return (
            f"Unsupported Hindi Kokoro symbol {self.invalid_symbol!r} "
            f"(U+{ord(self.invalid_symbol):04X}) in source token "
            f"{self.source_token!r}; raw={self.raw_ipa!r}, "
            f"normalized={self.normalized_ipa!r}"
        )


def transform_hindi_ipa(raw_ipa: str) -> str:
    """Apply only Hindi-safe compatibility cleanup to raw eSpeak IPA."""
    normalized = strip_espeak_language_markers(raw_ipa)
    return normalized.replace("^", "").replace("\u0361", "").replace("\u0329", "")


def validate_hindi_symbols(
    ipa: str,
    *,
    source_token: str = "",
    raw_ipa: str = "",
    strict: bool = True,
) -> list[str]:
    """Validate final Hindi labels against the stock Kokoro vocabulary."""
    valid, invalid = validate_for_kokoro(ipa, model=TARGET_MODEL)
    if valid:
        return []
    if strict:
        raise HindiVocabularyError(invalid[0], source_token, raw_ipa, ipa)
    return invalid


def model_profile_vocab() -> dict[str, int]:
    """Return an isolated copy of the stock target mapping for diagnostics."""
    return dict(get_vocab(TARGET_MODEL))


__all__ = [
    "PROFILE_NAME",
    "TARGET_MODEL",
    "HindiVocabularyError",
    "model_profile_vocab",
    "transform_hindi_ipa",
    "validate_hindi_symbols",
]
