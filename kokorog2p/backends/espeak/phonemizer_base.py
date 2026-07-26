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

    @staticmethod
    def _normalize_voice_code(value: str) -> str:
        return value.strip().lower().replace("_", "-")

    @classmethod
    def _is_mbrola_request(cls, language: str) -> bool:
        code = cls._normalize_voice_code(language)
        return code.startswith(("mb/", "mb-", "mbrola"))

    @staticmethod
    def _is_mbrola_voice(voice: Voice) -> bool:
        return voice.identifier.strip().lower().startswith("mb/")

    def _resolve_voice(self, language: str) -> tuple[str, Voice]:
        """Resolve a language to an espeak voice without implicit MBROLA use."""
        requested = self._normalize_voice_code(language)
        if not requested:
            raise RuntimeError('Invalid voice code ""')

        if self._is_mbrola_request(requested):
            voices = self.list_voices("mbrola")
            for voice in voices:
                if not self._is_mbrola_voice(voice):
                    continue
                identifier = voice.identifier
                aliases = {
                    self._normalize_voice_code(identifier),
                    self._normalize_voice_code(identifier[3:]),
                }
                if requested in aliases:
                    return identifier, voice
            raise RuntimeError(f'Invalid MBROLA voice code "{language}"')

        voices = self.list_voices(language)
        standard_voices = [v for v in voices if not self._is_mbrola_voice(v)]
        chosen = self._choose_standard_voice(requested, standard_voices)

        if chosen is None:
            voices = self.list_voices()
            standard_voices = [v for v in voices if not self._is_mbrola_voice(v)]
            chosen = self._choose_standard_voice(requested, standard_voices)

        if chosen is None:
            raise RuntimeError(
                f'Invalid standard espeak voice code "{language}" '
                "(MBROLA voices are excluded)"
            )

        return chosen.identifier, chosen

    @classmethod
    def _choose_standard_voice(
        cls,
        requested: str,
        voices: list[Voice],
    ) -> Voice | None:
        """Choose the best non-MBROLA voice while preserving espeak list order."""
        requested_base = requested.split("-", 1)[0]
        ranked: list[tuple[int, int, Voice]] = []

        for index, voice in enumerate(voices):
            if not voice.identifier or cls._is_mbrola_voice(voice):
                continue

            voice_language = cls._normalize_voice_code(voice.language)
            identifier = cls._normalize_voice_code(voice.identifier)
            identifier_name = identifier.rsplit("/", 1)[-1]

            if voice_language == requested:
                rank = 0
            elif identifier == requested or identifier_name == requested:
                rank = 1
            elif voice_language.split("-", 1)[0] == requested_base:
                rank = 2
            else:
                continue

            ranked.append((rank, index, voice))

        if not ranked:
            return None
        return min(ranked, key=lambda item: item[:2])[2]
