"""Deprecated compatibility facades over :mod:`espeakng_runtime`."""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from espeakng_runtime import EspeakRuntime, inspect_espeak

from kokorog2p.backends.espeak.voice import Voice


class RuntimePhonemizer:
    """Small stateful adapter retaining the historical phonemizer API."""

    _mode: Literal["native", "cli"] = "native"
    _custom_library: str | None = None
    _custom_data: str | None = None

    def __init__(
        self,
        language: str = "en-us",
        executable: str | None = None,
        library: str | None = None,
        data_path: str | Path | None = None,
        sep: str = "_",
        tie_char: str = "͡",
        timeout: float | None = None,
    ) -> None:
        self.language = language
        self.executable = executable or os.getenv("KOKOROG2P_ESPEAK_EXECUTABLE")
        self.sep = sep
        self.tie_char = tie_char
        self.timeout = timeout
        self._library_override = (
            library or self._custom_library or os.getenv("KOKOROG2P_ESPEAK_LIBRARY")
        )
        selected_data = (
            data_path or self._custom_data or os.getenv("KOKOROG2P_ESPEAK_DATA")
        )
        self._data_override = str(selected_data) if selected_data is not None else None
        self._runtime: EspeakRuntime | None = None
        self._voice_request: str | None = None
        self._resolved_voice: Voice | None = None

    @classmethod
    def set_library_path(cls, path: str | None) -> None:
        """Set a deprecated default for subsequently created instances."""
        cls._custom_library = path

    @classmethod
    def set_data_path(cls, path: str | None) -> None:
        """Set a deprecated default for subsequently created instances."""
        cls._custom_data = path

    @classmethod
    def is_available(cls) -> bool:
        """Return whether the configured eSpeak executable is discoverable."""
        return inspect_espeak(
            executable=os.getenv("KOKOROG2P_ESPEAK_EXECUTABLE") or None,
            library=os.getenv("KOKOROG2P_ESPEAK_LIBRARY") or None,
            data=os.getenv("KOKOROG2P_ESPEAK_DATA") or None,
        ).cli_available

    def _get_runtime(self) -> EspeakRuntime:
        if self._runtime is None:
            self._runtime = EspeakRuntime(
                mode=self._mode,
                executable=self.executable,
                library=self._library_override,
                data=self._data_override,
                timeout=self.timeout,
            )
        return self._runtime

    @property
    def version(self) -> tuple[int, ...]:
        return self._get_runtime().info.version_tuple

    @property
    def voice(self) -> Voice | None:
        return self._resolved_voice

    @property
    def voice_language(self) -> str | None:
        return (
            self._resolved_voice.language if self._resolved_voice is not None else None
        )

    @property
    def data_path(self) -> Path | None:
        value = self._get_runtime().info.data
        return Path(value) if value else None

    @property
    def library_path(self) -> Path | None:
        value = self._get_runtime().info.library
        return Path(value) if value else None

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        return [
            Voice.from_runtime(voice)
            for voice in self._get_runtime().list_voices(filter_name)
        ]

    def set_voice(self, voice: str) -> None:
        resolved = self._get_runtime().resolve_voice(voice)
        self._voice_request = voice
        self._resolved_voice = Voice.from_runtime(resolved)
        self.language = voice

    def _voice_identifier(self) -> str:
        if self._resolved_voice is None:
            raise RuntimeError("No eSpeak voice selected")
        return self._resolved_voice.identifier

    def phonemize(
        self,
        text: str,
        separator: str | None = None,
        use_tie: bool = False,
    ) -> str:
        return self._get_runtime().phonemize(
            text,
            voice=self._voice_identifier(),
            separator=self.sep if separator is None and not use_tie else separator,
            use_tie=use_tie,
            tie_char=self.tie_char,
        )

    def phonemize_many(
        self,
        texts: Sequence[str],
        use_tie: bool = False,
    ) -> list[str]:
        return self._get_runtime().phonemize_many(
            texts,
            voice=self._voice_identifier(),
            separator=self.sep if not use_tie else None,
            use_tie=use_tie,
            tie_char=self.tie_char,
        )

    def close(self) -> None:
        runtime = self._runtime
        self._runtime = None
        if runtime is not None:
            runtime.close()

    def __getstate__(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "executable": self.executable,
            "sep": self.sep,
            "tie_char": self.tie_char,
            "timeout": self.timeout,
            "library_override": self._library_override,
            "data_override": self._data_override,
            "voice_request": self._voice_request,
            "resolved_voice": self._resolved_voice,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        self.language = state["language"]
        self.executable = state["executable"]
        self.sep = state["sep"]
        self.tie_char = state["tie_char"]
        self.timeout = state["timeout"]
        self._library_override = state["library_override"]
        self._data_override = state["data_override"]
        self._voice_request = state["voice_request"]
        self._resolved_voice = state["resolved_voice"]
        self._runtime = None


class Phonemizer(RuntimePhonemizer):
    """Deprecated native compatibility facade."""

    _mode: Literal["native", "cli"] = "native"


class CliPhonemizer(RuntimePhonemizer):
    """Deprecated CLI compatibility facade."""

    def __init__(self, language: str = "en-us", **kwargs: Any) -> None:
        super().__init__(language=language, **kwargs)
        self.set_voice(language)

    _mode: Literal["native", "cli"] = "cli"


EspeakWrapper = Phonemizer

__all__ = ["CliPhonemizer", "EspeakWrapper", "Phonemizer", "RuntimePhonemizer"]
