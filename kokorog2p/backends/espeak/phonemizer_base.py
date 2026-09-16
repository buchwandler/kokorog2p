"""Deprecated compatibility protocol for eSpeak phonemizers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from kokorog2p.backends.espeak.voice import Voice


class EspeakPhonemizerBase(ABC):
    """Minimal historical interface retained for third-party subclasses.

    Voice discovery and resolution are delegated to ``espeakng-runtime`` by the
    built-in facades. This class no longer contains a second resolver.
    """

    @property
    @abstractmethod
    def version(self) -> tuple[int, ...]:
        raise NotImplementedError

    @property
    def voice(self) -> Voice | None:
        return None

    @abstractmethod
    def set_voice(self, language: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def phonemize(self, text: str, use_tie: bool = False) -> str:
        raise NotImplementedError

    def phonemize_many(self, texts: Sequence[str], use_tie: bool = False) -> list[str]:
        return [self.phonemize(text, use_tie=use_tie) for text in texts]

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        raise NotImplementedError

    @property
    def voice_language(self) -> str | None:
        return self.voice.language if self.voice is not None else None

    @property
    def library_path(self) -> Any:
        return None

    @property
    def data_path(self) -> Any:
        return None

    def __getstate__(self) -> dict[str, Any]:
        return self.__dict__.copy()

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.__dict__.update(state)
