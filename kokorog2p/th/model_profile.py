"""Wayu Thai model vocabulary and LexHint IPA adaptation policy."""

from __future__ import annotations

import unicodedata
from typing import Final

from kokorog2p.vocab import phonemes_to_ids, validate_for_kokoro

TARGET_MODEL: Final[str] = "wayu-kokoro-thai-v1"
TARGET_MODEL_ALIASES: Final[frozenset[str]] = frozenset({TARGET_MODEL, "wayu-thai"})
LOW_TONE: Final[str] = "˩"
RESERVED_TOKEN_IDS: Final[dict[str, int]] = {LOW_TONE: 7}

# LexHint uses standard IPA tone letters. These are the only observed tone
# contours that need a representation change for the Wayu vocabulary.
LEXHINT_TONE_MAP: Final[dict[str, str]] = {
    "˥˩": "↓",
    "˩˥": "↗",
    "˥˧": "↘",
    "˧˥": "↗",
    "˥": "↗",
    "˦": "→",
    "˧": "→",
    "˨": "↘",
}

LEXHINT_SYMBOL_MAP: Final[dict[str, str]] = {
    "\u031a": "",  # IPA unreleased-stop diacritic; no Wayu tokenizer token
    "\u0361": "",  # IPA combining tie bar; Wayu uses the untied affricate sequence
    "\u032f": "",  # IPA non-syllabic mark; Wayu encodes the vowel sequence itself
}


def adapt_lexhint_ipa(text: str) -> str:
    """Normalize observed LexHint IPA and map its standard tone contours."""
    adapted = unicodedata.normalize("NFC", text)
    for source, target in sorted(
        LEXHINT_TONE_MAP.items(), key=lambda item: -len(item[0])
    ):
        adapted = adapted.replace(source, target)

    adapted = "".join(LEXHINT_SYMBOL_MAP.get(char, char) for char in adapted)
    return " ".join(adapted.split())


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
    "LEXHINT_SYMBOL_MAP",
    "LEXHINT_TONE_MAP",
    "LOW_TONE",
    "RESERVED_TOKEN_IDS",
    "TARGET_MODEL",
    "TARGET_MODEL_ALIASES",
    "adapt_lexhint_ipa",
    "encode_output",
    "validate_output",
]
