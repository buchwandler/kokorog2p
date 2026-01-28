"""
Base class for espeak phonemizer backends.

This unifies the interface of:
- wrapper.Phonemizer (native/ctypes binding)
- cli_wrapper.CliPhonemizer (subprocess binding)

Design goals:
- Minimal required surface: version, set_voice, phonemize
- Optional properties for diagnostics and compatibility
- No dependency on Voice dataclass; backend implementations can expose more
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from kokorog2p.backends.espeak.voice import Voice

_VERSION_RE = re.compile(r"(\d+(?:\.\d+)+)")
_DATA_AT_RE = re.compile(r"(?i)\bData at:\s*([^\r\n]+)")


class EspeakPhonemizerBase(ABC):
    """Common interface for espeak phonemizer implementations."""

    def __init__(self) -> None:
        """Initialize the phonemizer."""
        self._reset_state()

    def _reset_state(self) -> None:
        self._version: tuple[int, ...] | None = None
        self._data_path: Path | None = None
        self._current_voice: Voice | None = None

    # --- Required API -----------------------------------------------------

    @property
    @abstractmethod
    def version(self) -> tuple[int, ...]:
        """Return espeak(-ng) version as tuple, e.g. (1, 52, 0)."""
        raise NotImplementedError

    @property
    def voice(self) -> Voice | None:
        return self._current_voice

    @abstractmethod
    def set_voice(self, language: str) -> None:
        """Select the voice/language used for subsequent phonemization."""
        raise NotImplementedError

    @abstractmethod
    def phonemize(self, text: str, use_tie: bool = False) -> str:
        """Convert text to IPA string.

        Implementations should:
        - Return "" for empty/whitespace input (recommended)
        - Use '_' separators when use_tie is False (recommended)
        - Remove/avoid tie characters when use_tie is False
        """
        raise NotImplementedError

    # --- Optional diagnostics / compatibility ----------------------------

    def __getstate__(self) -> dict[str, Any]:
        """Support pickling for multiprocessing."""
        return {
            "version": self._version,
            "data_path": self._data_path,
            "voice": self._current_voice,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore from pickle."""
        self._reset_state()
        self._version = state["version"]
        self._data_path = state["data_path"]
        self._current_voice = state["voice"]
        if self._current_voice:
            self.set_voice(self._current_voice.language)

    @property
    def voice_language(self) -> str | None:
        """Currently selected voice language code, if known."""
        return self._current_voice.language if self._current_voice else None

    @property
    def library_path(self) -> Path | None:
        """Native library path (ctypes backend); None for CLI backend."""
        return None

    @property
    def data_path(self) -> Path | None:
        """espeak-ng data path, if discoverable/known."""
        return None

    # --- Helpers ----------------------------------------------------------

    def supports_tie(self) -> bool:
        """Whether this backend supports tie character output for affricates."""
        # wrapper.Phonemizer enforces tie >= 1.49;
        # CLI typically supports tie in espeak-ng
        return self.version >= (1, 49)

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        """Optional: subclasses can override. Used by _resolve_voice()."""
        raise NotImplementedError

    @staticmethod
    def _parse_version_string(version_str: str) -> tuple[int, ...]:
        # Accept "1.51.1", "1.51.1-dev", "1.51.1-dev something"
        if not version_str.strip():
            return (0,)
        s = version_str.strip().split()[0]
        s = s.replace("-dev", "")
        s = s.split("-", 1)[0]
        parts = [p for p in s.split(".") if p.isdigit()]
        return tuple(int(p) for p in parts) if parts else (0,)

    @staticmethod
    def _parse_version_output(text: str) -> tuple[tuple[int, ...], Path | None]:
        """Parse CLI '--version' output that may contain 'Data at: ...'."""
        m = _VERSION_RE.search(text)
        ver = tuple(int(x) for x in m.group(1).split(".")) if m else (0,)

        dm = _DATA_AT_RE.search(text)
        data_path: Path | None = None
        if dm:
            data_str = dm.group(1).strip().strip('"').strip("'")
            if data_str:
                data_str = os.path.expanduser(data_str)
                data_path = Path(data_str)

        return ver, data_path

    def _resolve_voice(self, language: str) -> tuple[str, Voice]:
        """Shared voice-resolution algorithm (mbrola vs normal)."""
        if not language:
            raise RuntimeError('Invalid voice code ""')

        available: dict[str, str] = {}
        if "mb" in language:
            voices = self.list_voices("mbrola")
            available = {
                v.identifier[3:]: v.identifier
                for v in voices
                if v.identifier and v.identifier.startswith("mb/")
            }
        else:
            voices = self.list_voices(language)
            if not voices:
                voices = self.list_voices()
            for v in voices:
                if v.language and v.language not in available:
                    available[v.language] = v.identifier

        if language not in available:
            raise RuntimeError(f'Invalid voice code "{language}"')

        identifier = available[language]
        # choose a representative Voice object if we can
        chosen = next((v for v in voices if v.identifier == identifier), None)
        return identifier, (chosen or Voice(language=language, identifier=identifier))
