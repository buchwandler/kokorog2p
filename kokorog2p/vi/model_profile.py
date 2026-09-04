"""Kokoro model-facing policy for Vietnamese output."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from kokorog2p.vocab import get_vocab, phonemes_to_ids, validate_for_kokoro

from .render import TONE_RENDER, render_segments, render_tone
from .syllable import VietnameseTone

TARGET_MODEL: Final[str] = "1.0"
PROFILE_NAME: Final[str] = "VietnameseNorthern"
TONE_RENDER_KOKORO_10: Final[dict[VietnameseTone, str]] = TONE_RENDER


def adapt_lexhint_ipa(text: str, model: str = TARGET_MODEL) -> str:
    """Normalize LexHint IPA before the Vietnamese model boundary."""
    import unicodedata

    normalized = unicodedata.normalize("NFC", text)
    valid, invalid = validate_output(normalized, model=model)
    if not valid:
        raise ValueError(
            f"Kokoro model {model} does not support LexHint IPA: {''.join(invalid)}"
        )
    return normalized


def model_vocabulary(model: str = TARGET_MODEL) -> frozenset[str]:
    """Return the verified Kokoro character vocabulary for *model*."""
    return frozenset(get_vocab(model=model))


def adapt_segment(segment: str, model: str = TARGET_MODEL) -> str:
    """Validate one abstract rendered segment without silently deleting it."""
    invalid = sorted({char for char in segment if char not in model_vocabulary(model)})
    if invalid:
        raise ValueError(
            "Kokoro model "
            f"{model} does not support Vietnamese segment(s): {''.join(invalid)}"
        )
    return segment


def render_for_kokoro(
    segments: Iterable[str], tone: VietnameseTone, model: str = TARGET_MODEL
) -> str:
    """Render and validate one syllable for the selected Kokoro model."""
    rendered = render_segments(segments) + render_tone(tone)
    return "".join(adapt_segment(char, model=model) for char in rendered)


def validate_output(text: str, model: str = TARGET_MODEL) -> tuple[bool, list[str]]:
    """Validate all output symbols against the selected Kokoro vocabulary."""
    return validate_for_kokoro(text, model=model)


def encode_output(text: str, model: str = TARGET_MODEL) -> list[int]:
    """Encode validated Vietnamese output as Kokoro IDs."""
    valid, invalid = validate_output(text, model=model)
    if not valid:
        raise ValueError(
            f"Kokoro model {model} cannot encode Vietnamese output: {''.join(invalid)}"
        )
    return phonemes_to_ids(text, model=model)


# Public spelling matching the shared vocabulary API, kept here for callers that
# work with the Vietnamese profile directly.
validate_for_model = validate_output

__all__ = [
    "PROFILE_NAME",
    "TARGET_MODEL",
    "TONE_RENDER",
    "TONE_RENDER_KOKORO_10",
    "adapt_segment",
    "encode_output",
    "model_vocabulary",
    "render_for_kokoro",
    "render_tone",
    "validate_for_model",
    "validate_output",
]
