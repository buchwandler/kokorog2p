"""Optional, isolated Misaki reference provider adapters."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .types import ErrorInfo, ReferenceMetadata, ReferenceOutput

HEXGRAD_COMMIT = "fba1236595f2d2bf21d414ba6e57d25256afada3"
SEMIDARK_COMMIT = "9cda9268309160120fffee216280a9ca83ac4644"


class ReferenceUnavailable(RuntimeError):
    """Raised when an explicitly provisioned external reference is unavailable."""


class _MisakiProvider:
    metadata: ReferenceMetadata

    def _load(self) -> Any:
        try:
            import misaki
        except ImportError as exc:
            raise ReferenceUnavailable(
                f"{self.metadata.provider_id} is unavailable; install the pinned "
                "reference package in its isolated benchmark environment"
            ) from exc
        self._misaki = misaki
        return misaki

    def _metadata_with_version(self, misaki: Any) -> ReferenceMetadata:
        version = str(getattr(misaki, "__version__", self.metadata.package_version))
        return replace(self.metadata, package_version=version)


class HexgradEnglishMisakiProvider(_MisakiProvider):
    """Hexgrad Misaki English G2P for the US or GB Kokoro lineage."""

    def __init__(self, *, british: bool = False) -> None:
        language = "en-gb" if british else "en-us"
        self.british = british
        self.metadata = ReferenceMetadata(
            provider_id="hexgrad-misaki",
            repository="hexgrad/misaki",
            commit=HEXGRAD_COMMIT,
            package_version="0.9.4",
            frontend="misaki.en.G2P",
            configuration={
                "language": language,
                "trf": False,
                "british": british,
                "fallback": "espeak.EspeakFallback",
            },
        )
        self._g2p: Any = None

    def _load_g2p(self) -> Any:
        misaki = self._load()
        if self._g2p is None:
            from misaki import en, espeak

            self._g2p = en.G2P(
                trf=False,
                british=self.british,
                fallback=espeak.EspeakFallback(british=self.british),
            )
            self.metadata = self._metadata_with_version(misaki)
        return self._g2p

    def phonemize(
        self, text: str, *, case_id: str, language: str, model: str
    ) -> ReferenceOutput:
        try:
            phonemes, _tokens = self._load_g2p()(text)
            return ReferenceOutput(case_id, text, None, str(phonemes))
        except Exception as exc:
            return ReferenceOutput(
                case_id, text, None, error=ErrorInfo.from_exception(exc, "reference")
            )


class SemidarkGermanMisakiProvider(_MisakiProvider):
    """Semidark Misaki German ``DEG2P`` reference frontend."""

    def __init__(self) -> None:
        self.metadata = ReferenceMetadata(
            provider_id="semidark-misaki",
            repository="semidark/misaki",
            commit=SEMIDARK_COMMIT,
            package_version="0.9.4",
            frontend="misaki.de.DEG2P",
            configuration={"language": "de", "model": "1.0"},
        )
        self._g2p: Any = None
        self._normalizer: Any = None

    def _load_g2p(self) -> Any:
        misaki = self._load()
        if self._g2p is None:
            from misaki import de

            self._g2p = de.DEG2P()
            self._normalizer = getattr(de, "normalize_text_de", None)
            self.metadata = self._metadata_with_version(misaki)
        return self._g2p

    def phonemize(
        self, text: str, *, case_id: str, language: str, model: str
    ) -> ReferenceOutput:
        try:
            g2p = self._load_g2p()
            normalized = (
                self._normalizer(text) if self._normalizer is not None else None
            )
            phonemes, _tokens = g2p(text)
            return ReferenceOutput(case_id, text, normalized, str(phonemes))
        except Exception as exc:
            return ReferenceOutput(
                case_id, text, None, error=ErrorInfo.from_exception(exc, "reference")
            )


def unavailable_provider(metadata: ReferenceMetadata) -> None:
    """Raise the standard error used by callers that require an external provider."""
    raise ReferenceUnavailable(
        f"{metadata.provider_id} is unavailable; install its pinned package explicitly"
    )
