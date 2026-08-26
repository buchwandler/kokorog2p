"""Optional Arabic diacritization adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal, Protocol

DiacritizerMode = Literal["auto", "none", "camel-tools"]


class ArabicDiacritizer(Protocol):
    """Protocol implemented by Arabic token diacritizers."""

    def diacritize_tokens(self, tokens: Sequence[str]) -> list[str]:
        """Return one possibly enriched token for every input token."""
        ...


class ArabicDiacritizerError(RuntimeError):
    """Base error for optional Arabic diacritization failures."""


class ArabicDiacritizerDependencyError(ArabicDiacritizerError):
    """Raised when CAMeL Tools is not installed."""


class ArabicDiacritizerDataError(ArabicDiacritizerError):
    """Raised when CAMeL's pretrained MSA data is unavailable."""


class NoneDiacritizer:
    """Identity adapter for already-diacritized Arabic."""

    def diacritize_tokens(self, tokens: Sequence[str]) -> list[str]:
        return list(tokens)


class CamelMLEDiacritizer:
    """Lazy CAMeL Tools MSA MLE adapter.

    This adapter only calls CAMeL's local ``pretrained`` loader. It never invokes
    CAMeL data provisioning or any network/download operation.
    """

    def __init__(self) -> None:
        self._disambiguator: Any | None = None

    def _get_disambiguator(self) -> Any:
        if self._disambiguator is not None:
            return self._disambiguator
        try:
            from camel_tools.disambig.mle import MLEDisambiguator
        except ImportError as exc:
            raise ArabicDiacritizerDependencyError(
                "Arabic diacritizer 'camel-tools' is not installed. "
                "Install the optional Arabic diacritization dependency or use "
                "diacritizer='none' for already-diacritized text."
            ) from exc
        try:
            self._disambiguator = MLEDisambiguator.pretrained()
        except Exception as exc:
            raise ArabicDiacritizerDataError(
                "CAMeL MSA MLE data is unavailable. Provision "
                "disambig-mle-calima-msa-r13 using CAMeL Tools' documented data "
                "installation workflow. KokoroG2P does not download model data "
                "automatically."
            ) from exc
        return self._disambiguator

    def diacritize_tokens(self, tokens: Sequence[str]) -> list[str]:
        source_tokens = list(tokens)
        if not source_tokens:
            return []
        disambiguations = self._get_disambiguator().disambiguate(source_tokens)
        if len(disambiguations) != len(source_tokens):
            raise ArabicDiacritizerError(
                "CAMeL MLE diacritizer returned a different number of tokens "
                f"({len(disambiguations)}) than requested ({len(source_tokens)})."
            )
        result: list[str] = []
        for source, item in zip(source_tokens, disambiguations, strict=True):
            analyses = getattr(item, "analyses", ())
            if not analyses:
                result.append(source)
                continue
            first = analyses[0]
            analysis: Mapping[str, Any] | None = getattr(first, "analysis", None)
            if analysis is None and isinstance(first, Mapping):
                analysis = first.get("analysis")
            diacritized = analysis.get("diac") if analysis else None
            result.append(str(diacritized) if diacritized else source)
        return result


__all__ = [
    "ArabicDiacritizer",
    "ArabicDiacritizerDataError",
    "ArabicDiacritizerDependencyError",
    "ArabicDiacritizerError",
    "CamelMLEDiacritizer",
    "DiacritizerMode",
    "NoneDiacritizer",
]
