"""High-level wrapper for espeak-ng phonemization.

This module provides a convenient interface to the espeak-ng library for
converting text to phonemes. It handles library discovery, voice selection,
and phoneme conversion.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import ctypes.util
import os
import pathlib
import shutil
import sys
from pathlib import Path
from typing import Any

from kokorog2p.backends.espeak.api import PHONEMES_IPA, EspeakLibrary
from kokorog2p.backends.espeak.phonemizer_base import EspeakPhonemizerBase
from kokorog2p.backends.espeak.voice import (
    Voice,
    struct_to_voice,
    voice_to_struct,
)

# Environment variables for custom eSpeak paths
ENV_EXECUTABLE_PATH = "KOKOROG2P_ESPEAK_EXECUTABLE"
ENV_LIBRARY_PATH = "KOKOROG2P_ESPEAK_LIBRARY"
ENV_DATA_PATH = "KOKOROG2P_ESPEAK_DATA"


def find_espeak_executable() -> str | None:
    """Find the eSpeak executable using explicit configuration or PATH."""
    configured = os.environ.get(ENV_EXECUTABLE_PATH)
    if configured:
        path = Path(configured)
        if path.is_file():
            return str(path.resolve())
        return configured

    return shutil.which("espeak-ng") or shutil.which("espeak")


def _find_espeak_library_near_executable() -> Path | None:
    """Find an eSpeak library near its configured or PATH executable."""
    executable = find_espeak_executable()
    if not executable:
        return None

    executable_path = Path(executable)
    paths = [executable_path]
    try:
        resolved = executable_path.resolve()
    except OSError:
        resolved = executable_path
    if resolved != executable_path:
        paths.append(resolved)

    search_dirs: list[Path] = []
    for path in paths:
        for directory in (
            path.parent,
            path.parent.parent / "lib",
            path.parent.parent / "lib64",
        ):
            if directory not in search_dirs:
                search_dirs.append(directory)

    library_names = (
        "libespeak-ng.dylib",
        "libespeak.dylib",
        "libespeak-ng.so",
        "libespeak.so",
        "libespeak-ng.dll",
        "espeak-ng.dll",
        "libespeak.dll",
        "espeak.dll",
    )

    for directory in search_dirs:
        for name in library_names:
            candidate = directory / name
            if candidate.is_file():
                return candidate.resolve()

    return None


def _find_espeak_data_near_executable() -> Path | None:
    """Find the eSpeak data directory beside its executable."""
    executable = find_espeak_executable()
    if not executable:
        return None

    candidate = Path(executable).parent / "espeak-ng-data"
    if candidate.is_dir():
        return candidate.resolve()
    return None


def find_espeak_library() -> str:
    """Find the espeak-ng shared library.

    Search order:
    1. KOKOROG2P_ESPEAK_LIBRARY environment variable
    2. espeakng_loader package (if installed)
    3. System library (espeak-ng or espeak)
    4. Library near the configured or PATH eSpeak executable
    Returns:
        Path to the espeak library.

    Raises:
        RuntimeError: If no library can be found.
    """
    # Check environment variable
    if ENV_LIBRARY_PATH in os.environ:
        lib_path = pathlib.Path(os.environ[ENV_LIBRARY_PATH])
        if lib_path.is_file():
            return str(lib_path.resolve())
        raise RuntimeError(f"{ENV_LIBRARY_PATH}={lib_path} is not a valid file")

    # Try espeakng_loader package, except on Android. The published loader
    # package currently ships a macOS dylib there, which Android cannot load.
    if sys.platform != "android":
        try:
            import espeakng_loader

            loader_path = espeakng_loader.get_library_path()
            if loader_path and os.path.isfile(loader_path):
                return loader_path
        except ImportError:
            pass

    # Try system library
    lib_name = ctypes.util.find_library("espeak-ng") or ctypes.util.find_library(
        "espeak"
    )
    if lib_name:
        # On Android, ctypes.util.find_library() returns a soname rather than
        # an absolute path. Resolve it in the active Python prefixes so the
        # low-level API can copy the loaded library without dlinfo.
        if not os.path.isabs(lib_name):
            for prefix in (sys.prefix, sys.base_prefix):
                candidate = Path(prefix) / "lib" / lib_name
                if candidate.is_file():
                    return str(candidate.resolve())
        return lib_name

    executable_library = _find_espeak_library_near_executable()
    if executable_library is not None:
        return str(executable_library)

    raise RuntimeError(
        "Could not find espeak-ng library. "
        "Install espeak-ng or espeakng-loader package, or set "
        f"{ENV_LIBRARY_PATH} to the shared library path."
    )


def find_espeak_data() -> Path | None:
    """Find the espeak-ng data directory.

    Search order:
    1. KOKOROG2P_ESPEAK_DATA environment variable
    2. espeakng_loader package (if installed)
    3. Directory beside the configured or PATH executable
    4. None (let espeak find it)
    Returns:
        Path to data directory, or None to use espeak's default.
    """
    # Check environment variable
    if ENV_DATA_PATH in os.environ:
        data_path = pathlib.Path(os.environ[ENV_DATA_PATH])
        if data_path.is_dir():
            return data_path.resolve()
        raise RuntimeError(f"{ENV_DATA_PATH}={data_path} is not a valid directory")

    # Try espeakng_loader package
    try:
        import espeakng_loader

        loader_data = espeakng_loader.get_data_path()
        if loader_data and os.path.isdir(loader_data):
            return pathlib.Path(loader_data).resolve()
    except ImportError:
        pass

    executable_data = _find_espeak_data_near_executable()
    if executable_data is not None:
        return executable_data

    return None


def _coerce_path(data_str: str) -> Path:
    s = os.path.expanduser(data_str.strip().strip('"').strip("'"))
    return Path(s)


class Phonemizer(EspeakPhonemizerBase):
    """High-level interface for espeak-ng phonemization.

    This class provides a simple API for converting text to phonemes using
    espeak-ng. It handles library loading, voice selection, and phoneme
    conversion.

    Example:
        >>> phonemizer = Phonemizer()
        >>> phonemizer.set_voice("en-us")
        >>> phonemizer.phonemize("hello world")
        'həlˈoʊ wˈɜːld'
    """

    # Class-level overrides retained for backwards compatibility.
    _custom_library: str | None = None
    _custom_data: str | None = None

    def __init__(self, data_path: str | Path | None = None) -> None:
        """Initialize the wrapper with an optional instance data directory."""
        super().__init__()
        lib_path = self._custom_library or find_espeak_library()
        selected_data = data_path
        if selected_data is None:
            selected_data = self._custom_data or find_espeak_data()
        self._api = EspeakLibrary(lib_path, selected_data)
        if selected_data is not None:
            self._data_path = Path(selected_data).resolve()

    @classmethod
    def set_library_path(cls, path: str | None) -> None:
        """Set a custom library path for all instances.

        Args:
            path: Path to espeak library, or None to use auto-detection.
        """
        cls._custom_library = path

    @classmethod
    def set_data_path(cls, path: str | None) -> None:
        """Set a custom data path for all instances.

        Args:
            path: Path to espeak data directory, or None to use auto-detection.
        """
        cls._custom_data = path

    def __getstate__(self) -> dict[str, Any]:
        """Support pickling for multiprocessing."""
        return {
            "version": self._version,
            "data_path": self._data_path,
            "voice": self._current_voice,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restore from pickle."""
        self.__init__()
        self._version = state["version"]
        self._data_path = state["data_path"]
        self._current_voice = state["voice"]
        if self._current_voice:
            self.set_voice(self._current_voice.language)

    @property
    def version(self) -> tuple[int, ...]:
        if self._version is None:
            version_str, data_str = self._api.get_info()
            self._version = self._parse_version_string(version_str)
            if data_str and self._data_path is None:
                self._data_path = _coerce_path(data_str)
        return self._version

    @property
    def library_path(self) -> Path:
        """Get path to the espeak library."""
        return self._api.library_path

    @property
    def data_path(self) -> Path | None:
        if self._data_path is None:
            _, data_str = self._api.get_info()
            if data_str:
                self._data_path = _coerce_path(data_str)
        return self._data_path

    @property
    def voice(self) -> Voice | None:
        """Get the currently selected voice."""
        return self._current_voice

    @property
    def voice_language(self) -> str | None:
        return self._current_voice.language if self._current_voice else None

    def list_voices(self, filter_name: str | None = None) -> list[Voice]:
        """List available voices.

        Args:
            filter_name: Optional filter (e.g., "mbrola" for mbrola voices).

        Returns:
            List of available Voice objects.
        """
        # Create filter if specified
        voice_filter = None
        if filter_name:
            filter_voice = Voice(language=filter_name)
            voice_filter = voice_to_struct(filter_voice)

        # Get voices from library
        voice_ptrs = self._api.list_voices(voice_filter)

        voices: list[Voice] = []
        idx = 0
        while voice_ptrs[idx]:
            struct = voice_ptrs[idx].contents
            voices.append(struct_to_voice(struct))
            idx += 1

        return voices

    def set_voice(self, language: str) -> None:
        identifier, _ = self._resolve_voice(language)

        if self._api.set_voice_by_name(identifier) != 0:
            raise RuntimeError(f'Failed to set voice "{language}"')

        voice_struct = self._api.get_current_voice()
        self._current_voice = struct_to_voice(voice_struct)

    def phonemize(self, text: str, use_tie: bool = False) -> str:
        """Convert text to phonemes.

        Args:
            text: Text to phonemize.
            use_tie: If True, use tie character (͡) for affricates.
                     If False, use underscore separator.

        Returns:
            Phoneme string in IPA format.

        Raises:
            RuntimeError: If no voice is set.
        """
        if self._current_voice is None:
            raise RuntimeError("No voice set. Call set_voice() first.")

        if use_tie and self.version < (1, 49):
            raise RuntimeError("Tie option requires espeak >= 1.49")

        return self._api.text_to_phonemes(
            text,
            phoneme_mode=PHONEMES_IPA,
            separator="_" if not use_tie else None,
            use_tie=use_tie,
        )


# Backwards compatibility aliases
EspeakWrapper = Phonemizer
