"""Model-independent Vietnamese phoneme rendering."""

from __future__ import annotations

from collections.abc import Iterable

from .phonology import syllable_to_phones
from .syllable import VietnameseSyllable, VietnameseTone

TONE_RENDER: dict[VietnameseTone, str] = {
    VietnameseTone.NGANG: "→",
    VietnameseTone.HUYEN: "↘",
    VietnameseTone.HOI: "↘↗",
    VietnameseTone.NGA: "ʔ↗",
    VietnameseTone.SAC: "↗",
    VietnameseTone.NANG: "ʔ↓",
}


def render_segments(segments: Iterable[str]) -> str:
    """Join abstract segment strings into a model-independent sequence."""
    return "".join(segments)


def render_tone(tone: VietnameseTone) -> str:
    """Render a named tone using the initial broad Kokoro prosody profile."""
    try:
        return TONE_RENDER[tone]
    except KeyError as exc:
        raise ValueError(f"unsupported Vietnamese tone: {tone!r}") from exc


def render_syllable(syllable: VietnameseSyllable) -> str:
    """Render segmental phones followed by the named tone marker."""
    return render_segments(syllable_to_phones(syllable)) + render_tone(syllable.tone)


def render_syllables(syllables: Iterable[VietnameseSyllable]) -> str:
    """Render syllables with model word boundaries."""
    return " ".join(render_syllable(syllable) for syllable in syllables)


__all__ = [
    "TONE_RENDER",
    "render_segments",
    "render_syllable",
    "render_syllables",
    "render_tone",
]
