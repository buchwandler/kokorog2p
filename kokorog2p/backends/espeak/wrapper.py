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
from pathlib import Path
from typing import Any

from kokorog2p.backends.espeak.api import PHONEMES_IPA, EspeakLibrary
from kokorog2p.backends.espeak.phonemizer_base import EspeakPhonemizerBase
from kokorog2p.backends.espeak.voice import (
    Voice,
    struct_to_voice,
    voice_to_struct,
)

# Environment variable for custom library path
ENV_LIBRARY_PATH = "KOKOROG2P_ESPEAK_LIBRARY"
ENV_DATA_PATH = "KOKOROG2P_ESPEAK_DATA"


def find_espeak_library() -> str:
    """Find the espeak-ng shared library.

    Search order:
    1. KOKOROG2P_ESPEAK_LIBRARY environment variable
    2. espeakng_loader package (if installed)
    3. System library (espeak-ng or espeak)

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

    # Try espeakng_loader package
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
        return lib_name

    raise RuntimeError(
        "Could not find espeak-ng library. "
        "Install espeak-ng or espeakng-loader package."
    )


def find_espeak_data() -> Path | None:
    """Find the espeak-ng data directory.

    Search order:
    1. KOKOROG2P_ESPEAK_DATA environment variable
    2. espeakng_loader package (if installed)
    3. None (let espeak find it)

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

    # Class-level overrides for library/data paths
    _custom_library: str | None = None
    _custom_data: str | None = None

    def __init__(self) -> None:
        """Initialize the phonemizer.

        Raises:
            RuntimeError: If espeak-ng library cannot be loaded.
        """
        super().__init__()  # <-- shared state init here

        # Find library and data paths
        lib_path = self._custom_library or find_espeak_library()
        data_path = self._custom_data or find_espeak_data()

        # Initialize low-level API
        self._api = EspeakLibrary(lib_path, data_path)

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
