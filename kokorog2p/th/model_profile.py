"""Wayu Thai model vocabulary and TLTK adaptation policy."""

from __future__ import annotations

from typing import Final

from kokorog2p.vocab import phonemes_to_ids, validate_for_kokoro

TARGET_MODEL: Final[str] = "wayu-kokoro-thai-v1"
TARGET_MODEL_ALIASES: Final[frozenset[str]] = frozenset({TARGET_MODEL, "wayu-thai"})
LOW_TONE: Final[str] = "˩"
RESERVED_TOKEN_IDS: Final[dict[str, int]] = {LOW_TONE: 7}
TLTK_TONE_MAP: Final[dict[str, str]] = {
    "1": "→",
    "2": LOW_TONE,
    "3": "↘",
    "4": "↗",
    "5": "↓",
}
TLTK_PHONE_REMAP: Final[dict[str, str]] = {"ᴐ": "ɔ"}
TONE_SYMBOLS: Final[frozenset[str]] = frozenset(TLTK_TONE_MAP.values())


def clean_engine_output(text: str) -> str:
    """Remove formatting artifacts and apply the model's phone spelling."""
    cleaned = text.replace("ᴐ", "ɔ")
    for marker in ("|", "/", "<syl>", "</syl>", "<s>", "</s>"):
        cleaned = cleaned.replace(marker, "")
    return " ".join(cleaned.split())


def adapt_tltk_output(text: str) -> str:
    """Convert TLTK tone digits only when they follow a phone character."""
    cleaned = clean_engine_output(text)
    output: list[str] = []
    for index, char in enumerate(cleaned):
        if char in TLTK_TONE_MAP and index > 0 and not cleaned[index - 1].isdigit():
            output.append(TLTK_TONE_MAP[char])
        else:
            output.append(char)
    return "".join(output)


def validate_output(text: str, model: str = TARGET_MODEL) -> tuple[bool, list[str]]:
    """Validate Thai output against the selected model profile."""
    return validate_for_kokoro(text, model=model)


def encode_output(text: str, model: str = TARGET_MODEL) -> list[int]:
    """Encode validated Thai output for the target model."""
    valid, invalid = validate_output(text, model=model)
    if not valid:
        raise ValueError(
            f"Kokoro model {model} cannot encode Thai output: {''.join(invalid)}"
        )
    return phonemes_to_ids(text, model=model)


__all__ = [
    "LOW_TONE",
    "RESERVED_TOKEN_IDS",
    "TARGET_MODEL",
    "TARGET_MODEL_ALIASES",
    "TLTK_PHONE_REMAP",
    "TLTK_TONE_MAP",
    "TONE_SYMBOLS",
    "adapt_tltk_output",
    "clean_engine_output",
    "encode_output",
    "validate_output",
]
