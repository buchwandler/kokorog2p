"""Compatibility voice records for the runtime-owned eSpeak inventory."""

from __future__ import annotations

from dataclasses import dataclass

from espeakng_runtime import Voice as RuntimeVoice


@dataclass(frozen=True)
class Voice:
    """Field-compatible view of an ``espeakng-runtime`` voice."""

    name: str = ""
    language: str = ""
    identifier: str = ""
    gender: int = 0
    age: int = 0

    @classmethod
    def from_language(cls, language: str) -> Voice:
        return cls(language=language)

    @classmethod
    def from_runtime(cls, voice: RuntimeVoice) -> Voice:
        return cls(
            name=voice.name,
            language=voice.language,
            identifier=voice.identifier,
            gender=voice.gender,
            age=voice.age,
        )


EspeakVoice = Voice

__all__ = ["EspeakVoice", "Voice"]
