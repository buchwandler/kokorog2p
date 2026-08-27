"""Raw Russian eSpeak integration with explicit-stress capability checks."""

from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Protocol


class RussianEspeakError(RuntimeError):
    """Raised when the Russian eSpeak backend cannot provide required behavior."""


class _RawBackend(Protocol):
    language: str

    def phonemize(
        self,
        text: str,
        *,
        convert_to_kokoro: bool = True,
        remove_punctuation: bool = True,
    ) -> str: ...


_PROBE_FORMS = ("за́мок", "замо́к")
_probe_cache: dict[tuple[object, ...], bool] = {}
_probe_lock = RLock()


def _engine_identity(engine: object) -> tuple[object, ...]:
    data_path = getattr(engine, "data_path", None)
    executable = getattr(engine, "executable", None)
    return (type(engine), str(data_path) if data_path is not None else None, executable)


def supports_combining_acute(engine: RussianEspeakEngine | _RawBackend) -> bool:
    """Return whether an engine distinguishes two explicitly stressed forms.

    The probe is intentionally behavioral rather than version based. Results are
    cached per backend type, executable, and resolved data path.
    """
    key = _engine_identity(engine)
    with _probe_lock:
        if key in _probe_cache:
            return _probe_cache[key]
    try:
        if isinstance(engine, RussianEspeakEngine):
            results = [
                engine.backend.phonemize(
                    form, convert_to_kokoro=False, remove_punctuation=False
                )
                for form in _PROBE_FORMS
            ]
        else:
            results = [engine.phonemize_marked(form) for form in _PROBE_FORMS]  # type: ignore[attr-defined]
        supported = bool(results[0] and results[1] and results[0] != results[1])
    except Exception:
        supported = False
    with _probe_lock:
        _probe_cache[key] = supported
    return supported


def clear_stress_probe_cache() -> None:
    """Clear cached capability results, primarily for isolated tests."""
    with _probe_lock:
        _probe_cache.clear()


class RussianEspeakEngine:
    """Produce raw IPA for Russian text without Kokoro symbol conversion."""

    def __init__(
        self,
        *,
        data_path: str | Path | None = None,
        use_cli: bool = False,
        strict_stress: bool = True,
        backend: _RawBackend | None = None,
    ) -> None:
        self.data_path = Path(data_path).resolve() if data_path is not None else None
        self.use_cli = use_cli
        self.strict_stress = strict_stress
        self._backend = backend
        if strict_stress and backend is not None and not supports_combining_acute(self):
            raise RussianEspeakError(self._stress_error())

    @property
    def backend(self) -> _RawBackend:
        if self._backend is None:
            from kokorog2p.backends.espeak import EspeakBackend

            self._backend = EspeakBackend(
                language="ru",
                with_stress=True,
                use_cli=self.use_cli,
                data_path=self.data_path,
            )
        return self._backend

    @property
    def resolved_data_path(self) -> Path | None:
        path = getattr(self.backend, "data_path", None)
        return Path(path) if path is not None else self.data_path

    def _stress_error(self) -> str:
        return (
            "Russian G2P requires eSpeak Russian data that honors U+0301 "
            "combining-acute stress. The active data path did not pass the stress "
            "capability probe. Configure a compatible eSpeak data directory or "
            "install a supported eSpeak-ng build."
        )

    def ensure_stress_capability(self) -> None:
        if self.strict_stress and not supports_combining_acute(self):
            raise RussianEspeakError(self._stress_error())

    def phonemize_marked(self, text: str) -> str:
        """Phonemize combining-acute annotated Russian and return raw eSpeak IPA."""
        self.ensure_stress_capability()
        try:
            return self.backend.phonemize(
                text,
                convert_to_kokoro=False,
                remove_punctuation=False,
            )
        except Exception as exc:
            raise RussianEspeakError(
                f"Russian eSpeak failed for {text!r}: {exc}"
            ) from exc

    def __repr__(self) -> str:
        return (
            f"RussianEspeakEngine(data_path={self.resolved_data_path!r}, "
            f"use_cli={self.use_cli}, strict_stress={self.strict_stress})"
        )
