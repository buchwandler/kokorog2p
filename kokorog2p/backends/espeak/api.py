"""Low-level ctypes bindings to the espeak-ng shared library.

This module provides direct bindings to the espeak-ng C API functions
defined in speak_lib.h. It handles library loading, initialization,
and cleanup.

Copyright 2024 kokorog2p contributors
Licensed under the Apache License, Version 2.0
"""

import atexit
import ctypes
import ctypes.util
import os
import pathlib
import shutil
import sys
import tempfile
import warnings
import weakref
from pathlib import Path
from typing import Any

from kokorog2p.backends.espeak.voice import VoiceStruct

# dlinfo is used on Linux/MacOS to get library path
if sys.platform != "win32":
    try:
        import dlinfo

        HAS_DLINFO = True
    except ImportError:
        HAS_DLINFO = False
else:
    HAS_DLINFO = False


# espeak_AUDIO_OUTPUT enum values from speak_lib.h
AUDIO_OUTPUT_PLAYBACK = 0
AUDIO_OUTPUT_RETRIEVAL = 1
AUDIO_OUTPUT_SYNCHRONOUS = 2
AUDIO_OUTPUT_SYNCH_PLAYBACK = 3

# Text encoding flags from speak_lib.h
CHARS_AUTO = 0
CHARS_UTF8 = 1
CHARS_8BIT = 2
CHARS_WCHAR = 3
CHARS_16BIT = 4

# Phoneme mode flags from speak_lib.h
PHONEMES_SHOW = 0x01
PHONEMES_IPA = 0x02
PHONEMES_TRACE = 0x08
PHONEMES_MBROLA = 0x10
PHONEMES_TIE = 0x80


def _find_library_path(lib: ctypes.CDLL) -> Path:
    """Get the absolute path of a loaded shared library.

    Args:
        lib: A loaded ctypes CDLL instance.

    Returns:
        Absolute path to the library file.

    Raises:
        RuntimeError: If the library path cannot be determined.
    """
    # Try the _name attribute first (works on Windows and sometimes Linux)
    name_path = pathlib.Path(lib._name).resolve()
    if name_path.is_file():
        return name_path

    # On Linux/MacOS, use dlinfo if available
    if HAS_DLINFO:
        try:
            return pathlib.Path(dlinfo.DLInfo(lib).path).resolve()
        except Exception:
            pass

    raise RuntimeError(f"Cannot determine path for library: {lib._name}")


class EspeakLibrary:
    """Low-level bindings to the espeak-ng shared library.

    This class handles loading the espeak-ng library, initializing it,
    and providing access to the C API functions. Each instance gets its
    own copy of the library to support multiple independent instances.

    The library uses espeak-ng's synchronous mode for phonemization.
    """

    def __init__(
        self,
        library_path: str | Path,
        data_path: str | Path | None = None,
    ) -> None:
        """Initialize the espeak library bindings.

        Args:
            library_path: Path to the espeak-ng shared library.
            data_path: Optional path to espeak-ng data directory.

        Raises:
            RuntimeError: If the library cannot be loaded or initialized.
        """
        self._lib: ctypes.CDLL | None = None
        self._temp_dir: str | None = None
        self._original_path: Path | None = None

        # Convert data_path to bytes for C API
        data_bytes: bytes | None = None
        if data_path is not None:
            data_bytes = str(data_path).encode("utf-8")

        # Load library to get its actual path
        try:
            temp_lib = ctypes.cdll.LoadLibrary(str(library_path))
            self._original_path = _find_library_path(temp_lib)
            del temp_lib
        except OSError as e:
            raise RuntimeError(f"Failed to load espeak library: {e}") from None

        # Create a temporary copy of the library
        # This is needed because espeak-ng uses global state, so multiple
        # instances require separate library copies
        self._temp_dir = tempfile.mkdtemp(prefix="espeak_")
        lib_copy = pathlib.Path(self._temp_dir) / self._original_path.name
        shutil.copy(self._original_path, lib_copy, follow_symlinks=False)

        # Register cleanup
        if sys.platform == "win32":
            atexit.register(self._cleanup_windows)
        else:
            weakref.finalize(self, self._cleanup, None, self._temp_dir)

        # Load the copy and initialize
        self._lib = ctypes.cdll.LoadLibrary(str(lib_copy))

        # espeak_Initialize(output, buflength, path, options)
        # output=AUDIO_OUTPUT_SYNCHRONOUS (0x02), buflength=0, options=0
        try:
            result = self._lib.espeak_Initialize(
                AUDIO_OUTPUT_SYNCHRONOUS, 0, data_bytes, 0
            )
            if result <= 0:
                raise RuntimeError("espeak_Initialize returned error")
        except AttributeError as e:
            raise RuntimeError(
                "Invalid espeak library - missing espeak_Initialize"
            ) from e

        # Update finalizer with the loaded library
        if sys.platform != "win32":
            weakref.finalize(self, self._cleanup, self._lib, self._temp_dir)

    def _cleanup_windows(self) -> None:
        """Cleanup for Windows (atexit handler)."""
        self._cleanup(self._lib, self._temp_dir)

    @staticmethod
    def _cleanup(lib: ctypes.CDLL | None, temp_dir: str | None) -> None:
        """Clean up library resources.

        Args:
            lib: The loaded library to terminate.
            temp_dir: Temporary directory to remove.
        """
        # Terminate espeak
        if lib is not None:
            try:
                lib.espeak_Terminate()
            except (AttributeError, OSError):
                pass

            # On Windows, unload the DLL so we can delete it
            if sys.platform == "win32":
                try:
                    import _ctypes

                    _ctypes.FreeLibrary(lib._handle)
                except (ImportError, AttributeError, OSError):
                    pass

        # Remove temporary directory
        if temp_dir and os.path.isdir(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

    @property
    def library_path(self) -> Path:
        """Path to the original espeak library."""
        if self._original_path is None:
            raise RuntimeError("Library not loaded")
        return self._original_path

    @property
    def temp_dir(self) -> str | None:
        """Temporary directory containing library copy."""
        return self._temp_dir

    def get_info(self) -> tuple[str, str]:
        """Get espeak version and data path.

        Returns:
            Tuple of (version_string, data_path).

        Raises:
            RuntimeError: If library not loaded.
        """
        if self._lib is None:
            raise RuntimeError("Library not loaded")

        # const char *espeak_Info(const char **path_data)
        func = self._lib.espeak_Info
        func.restype = ctypes.c_char_p

        path_ptr = ctypes.c_char_p()
        version = func(ctypes.byref(path_ptr))

        version_str = version.decode("utf-8") if version else ""
        path_str = path_ptr.value.decode("utf-8") if path_ptr.value else ""

        return version_str, path_str

    def list_voices(self, voice_filter: VoiceStruct | None = None) -> Any:
        """List available voices.

        Args:
            voice_filter: Optional filter for voice selection.

        Returns:
            Array of pointers to VoiceStruct, terminated by NULL.

        Raises:
            RuntimeError: If library not loaded.
        """
        if self._lib is None:
            raise RuntimeError("Library not loaded")

        # const espeak_VOICE **espeak_ListVoices(espeak_VOICE *voice_spec)
        func = self._lib.espeak_ListVoices
        func.argtypes = [ctypes.POINTER(VoiceStruct)]
        func.restype = ctypes.POINTER(ctypes.POINTER(VoiceStruct))

        filter_ptr = ctypes.pointer(voice_filter) if voice_filter else None
        return func(filter_ptr)

    def set_voice_by_name(self, name: str) -> int:
        """Set the voice by name/identifier.

        Args:
            name: Voice name or identifier.

        Returns:
            0 on success, non-zero on failure.

        Raises:
            RuntimeError: If library not loaded.
        """
        if self._lib is None:
            raise RuntimeError("Library not loaded")

        # espeak_ERROR espeak_SetVoiceByName(const char *name)
        func = self._lib.espeak_SetVoiceByName
        func.argtypes = [ctypes.c_char_p]
        func.restype = ctypes.c_int

        return func(name.encode("utf-8"))

    def get_current_voice(self) -> VoiceStruct:
        """Get the currently selected voice.

        Returns:
            VoiceStruct for the current voice.

        Raises:
            RuntimeError: If library not loaded.
        """
        if self._lib is None:
            raise RuntimeError("Library not loaded")

        # espeak_VOICE *espeak_GetCurrentVoice(void)
        func = self._lib.espeak_GetCurrentVoice
        func.restype = ctypes.POINTER(VoiceStruct)

        return func().contents

    def text_to_phonemes(
        self,
        text: str,
        phoneme_mode: int = PHONEMES_IPA,
        separator: str | None = None,
        use_tie: bool = False,
    ) -> str:
        """Convert text to phonemes.

        Args:
            text: Text to convert.
            phoneme_mode: Phoneme output mode (default: IPA).
            separator: Character to separate phonemes (default: None).
            use_tie: If True, use tie character for multi-letter phonemes.

        Returns:
            Phoneme string.

        Raises:
            RuntimeError: If library not loaded.
        """
        if self._lib is None:
            raise RuntimeError("Library not loaded")

        # const char *espeak_TextToPhonemes(const void **textptr,
        #                                   int textmode, int phonememode)
        func = self._lib.espeak_TextToPhonemes
        func.restype = ctypes.c_char_p
        func.argtypes = [
            ctypes.POINTER(ctypes.c_char_p),
            ctypes.c_int,
            ctypes.c_int,
        ]

        # Build phoneme_mode flags
        # bit 1: 1 = IPA output
        # bit 7: use separator from bits 8-23
        # bits 8-23: separator character
        mode = phoneme_mode

        if use_tie:
            # Use tie character (U+0361) between phoneme parts
            mode |= PHONEMES_TIE
            mode |= ord("͡") << 8
        elif separator:
            mode |= ord(separator[0]) << 8

        # Create pointer to text
        text_bytes = text.encode("utf-8")
        text_ptr = ctypes.pointer(ctypes.c_char_p(text_bytes))

        # Text mode: 1 = UTF-8 input
        text_mode = CHARS_UTF8

        # Collect all phoneme chunks
        result_parts = []
        while text_ptr.contents.value is not None:
            prev_value = text_ptr.contents.value
            phonemes = func(text_ptr, text_mode, mode)
            if phonemes:
                result_parts.append(phonemes.decode("utf-8"))
            if text_ptr.contents.value == prev_value:
                warnings.warn(
                    "espeak_TextToPhonemes made no progress; "
                    "stopping to avoid infinite loop.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                break

        return " ".join(result_parts)
