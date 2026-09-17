"""Kokoro-facing adapter for the shared :mod:`espeakng_runtime` package."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from espeakng_runtime import EspeakRuntime, RuntimeInfo

from kokorog2p.phonemes import from_espeak, strip_espeak_language_markers

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EspeakBackendInfo:
    """Stable, non-initializing description of the direct eSpeak adapter."""

    implementation: Literal["native", "cli", "uninitialized"]
    executable: str | None
    library_path: str | None
    data_path: str | None
    native_error_type: str | None
    native_error: str | None
    requested_mode: str | None = None
    source: str | None = None
    version: str | None = None
    fallback_code: str | None = None
    fallback_reason: str | None = None


class EspeakBackend:
    """Apply Kokoro phoneme policy on top of ``EspeakRuntime``.

    Runtime discovery, native calls, CLI calls, voice resolution, batching, and
    lifecycle are owned by ``espeakng-runtime``. This adapter owns only the
    Kokoro conversion and punctuation policy.
    """

    def __init__(
        self,
        language: str = "en-us",
        with_stress: bool = True,
        tie: str = "^",
        use_cli: bool = False,
        data_path: str | Path | None = None,
    ) -> None:
        self.language = language
        self.with_stress = with_stress
        self.tie = tie
        self.use_cli = use_cli
        # Keep the caller's spelling intact; Path normalizes POSIX-looking paths
        # into backslashes when this code runs on Windows. The runtime accepts
        # path-like strings directly and should receive the configured override
        # unchanged across platforms.
        self.data_path = data_path
        self._runtime: EspeakRuntime | None = None
        self._runtime_error: Exception | None = None

    def _make_runtime(self) -> EspeakRuntime:
        """Construct the shared runtime using Kokoro's legacy overrides."""
        return EspeakRuntime(
            mode="cli" if self.use_cli else "auto",
            executable=os.getenv("KOKOROG2P_ESPEAK_EXECUTABLE") or None,
            library=os.getenv("KOKOROG2P_ESPEAK_LIBRARY") or None,
            data=str(self.data_path)
            if self.data_path is not None
            else os.getenv("KOKOROG2P_ESPEAK_DATA") or None,
        )

    def _get_runtime(self) -> EspeakRuntime:
        if self._runtime is None:
            self._runtime = self._make_runtime()
        return self._runtime

    @property
    def runtime_info(self) -> RuntimeInfo | None:
        """Return shared-runtime diagnostics after initialization, if any."""
        return None if self._runtime is None else self._runtime.info

    @property
    def native_error(self) -> Exception | None:
        """Deprecated compatibility view of automatic native fallback."""
        if self._runtime_error is not None:
            return self._runtime_error
        runtime = self._runtime
        if runtime is None:
            return None
        info = runtime.info
        if info.fallback_code is None:
            return None
        return RuntimeError(info.fallback_reason or info.fallback_code)

    @property
    def wrapper(self) -> Any:
        """Return the initialized runtime for legacy callers.

        New code should use :attr:`runtime_info` and the adapter methods. The
        old wrapper modules remain available as separate compatibility facades.
        """
        return self._get_runtime()

    @property
    def info(self) -> EspeakBackendInfo:
        """Return compatibility diagnostics without initializing the runtime."""
        if self._runtime is None:
            error = self._runtime_error
            return EspeakBackendInfo(
                implementation="uninitialized",
                executable=None,
                library_path=None,
                data_path=str(self.data_path) if self.data_path is not None else None,
                native_error_type=type(error).__name__ if error is not None else None,
                native_error=str(error) if error is not None else None,
            )

        runtime_info = self._runtime.info
        error = self.native_error
        return EspeakBackendInfo(
            implementation=runtime_info.implementation,
            executable=runtime_info.executable,
            library_path=runtime_info.library,
            data_path=runtime_info.data,
            native_error_type=type(error).__name__ if error is not None else None,
            native_error=str(error) if error is not None else None,
            requested_mode=runtime_info.requested_mode,
            source=runtime_info.source,
            version=runtime_info.version,
            fallback_code=runtime_info.fallback_code,
            fallback_reason=runtime_info.fallback_reason,
        )

    def diagnostics(self) -> EspeakBackendInfo:
        """Compatibility method returning :attr:`info`."""
        return self.info

    @property
    def is_british(self) -> bool:
        return self.language.lower() in ("en-gb", "en_gb")

    def remove_punctuation(self, text: str) -> str:
        """Normalize punctuation while preserving Kokoro's existing policy."""
        apos_protect = "__APOS__"
        hyphen_protect = "__HYPHEN__"
        text = re.sub(r"(?<=\w)'(?=\w)", apos_protect, text)
        text = re.sub(r"(?<=\w)-(?=\w)", hyphen_protect, text)
        text = re.sub(r"[\"']", "", text)
        text = re.sub(r"\s+([.,;:!?])", r"\1", text)
        text = re.sub(r"([?!;:,])\1+", r"\1", text)
        text = re.sub(r"\.{2,}", ".", text)
        text = re.sub(r"(?<!\w)[?!;:,](?!\w)", "", text)
        text = re.sub(r"(?<!\w)\.(?!\w)", "", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"([.,;:!?])(?=\w)", r"\1 ", text)
        return text.replace(apos_protect, "'").replace(hyphen_protect, "-").strip()

    def _raw_options(self) -> dict[str, object]:
        use_tie = self.tie == "^"
        return {
            "separator": None if use_tie else "_",
            "use_tie": use_tie,
            "tie_char": "͡",
        }

    def _convert_raw_phonemes(self, raw: str) -> str:
        raw = strip_espeak_language_markers(raw)
        return from_espeak(raw, british=self.is_british)

    def phonemize(
        self,
        text: str,
        convert_to_kokoro: bool = True,
        remove_punctuation: bool = True,
    ) -> str:
        if remove_punctuation:
            text = self.remove_punctuation(text)
        raw = self._get_runtime().phonemize(
            text,
            voice=self.language,
            **self._raw_options(),
        )
        if not convert_to_kokoro:
            return raw
        result = self._convert_raw_phonemes(raw)
        return result

    def phonemize_list(
        self,
        texts: list[str],
        convert_to_kokoro: bool = True,
        remove_punctuation: bool = True,
    ) -> list[str]:
        """Convert multiple texts while preserving the historical list API."""
        return self.phonemize_many(
            texts,
            convert_to_kokoro=convert_to_kokoro,
            remove_punctuation=remove_punctuation,
        )

    def phonemize_many(
        self,
        texts: Sequence[str],
        convert_to_kokoro: bool = True,
        remove_punctuation: bool = True,
    ) -> list[str]:
        """Convert independently framed texts through the runtime batch API."""
        if remove_punctuation:
            texts = [self.remove_punctuation(t) for t in texts]
        raw_items = self._get_runtime().phonemize_many(
            texts,
            voice=self.language,
            **self._raw_options(),
        )
        if not convert_to_kokoro:
            return raw_items
        return [self._convert_raw_phonemes(item) for item in raw_items]

    def word_phonemes(self, word: str, convert_to_kokoro: bool = True) -> str:
        """Convert one word and remove output separators."""
        result = self.phonemize(word, convert_to_kokoro, remove_punctuation=True)
        return result.strip().replace("_", "")

    @property
    def version(self) -> str:
        """Return the runtime's reported eSpeak version."""
        version = self._get_runtime().info.version
        return version or ""

    def close(self) -> None:
        """Release the runtime; repeated calls are safe."""
        runtime = self._runtime
        self._runtime = None
        if runtime is not None:
            runtime.close()

    def __getstate__(self) -> dict[str, object]:
        state = self.__dict__.copy()
        state["_runtime"] = None
        return state

    def __setstate__(self, state: dict[str, object]) -> None:
        self.__dict__.update(state)
        self._runtime = None

    def __repr__(self) -> str:
        return f"EspeakBackend(language={self.language!r})"
