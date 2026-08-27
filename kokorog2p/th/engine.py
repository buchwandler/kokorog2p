"""Lazy TLTK adapter with source-aware recovery for Thai pronunciation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from threading import RLock
from types import ModuleType
from typing import Any

from .model_profile import adapt_tltk_output


class ThaiG2PError(RuntimeError):
    """Raised when Thai pronunciation cannot be provided or recovered."""


@dataclass
class EngineResult:
    """Result from one Thai source chunk."""

    source: str
    raw_ipa: str = ""
    used_fallback: bool = False
    unrecovered: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def phonemes(self) -> str:
        return adapt_tltk_output(self.raw_ipa)


class ThaiEngine:
    """Small, serializable adapter around the optional Thai dependencies."""

    def __init__(
        self,
        *,
        strict: bool = True,
        tltk_module: ModuleType | Any | None = None,
        pythainlp_module: ModuleType | Any | None = None,
    ) -> None:
        self.strict = strict
        self._lock = RLock()
        self._tltk = tltk_module or self._load_tltk()
        self._pythainlp = pythainlp_module or self._load_pythainlp()

    @staticmethod
    def _load_tltk() -> Any:
        try:
            import tltk
        except ImportError as exc:
            raise ImportError(
                "Thai G2P requires the optional Thai dependencies. "
                'Install with: python -m pip install "kokorog2p[th]"'
            ) from exc
        return tltk

    @staticmethod
    def _load_pythainlp() -> Any:
        try:
            import pythainlp
        except ImportError as exc:
            raise ImportError(
                "Thai G2P requires the optional Thai dependencies. "
                'Install with: python -m pip install "kokorog2p[th]"'
            ) from exc
        return pythainlp

    def _call_tltk(self, source: str) -> str:
        with self._lock:
            result = self._tltk.nlp.th2ipa(source)
        if result is None:
            return ""
        return str(result).strip()

    @staticmethod
    def _looks_truncated(source: str, result: str) -> bool:
        source_units = [part for part in re.split(r"\s+", source.strip()) if part]
        if len(source_units) <= 1:
            return False
        output_units = [part for part in re.split(r"\s+", result.strip()) if part]
        return len(output_units) < len(source_units) and len(result) < len(
            "".join(source_units)
        )

    def _segment_units(self, source: str, kind: str) -> tuple[list[str], list[str]]:
        tokenizer = getattr(self._pythainlp, kind, None)
        if tokenizer is None:
            tokenizer = getattr(getattr(self._pythainlp, "tokenize", None), kind, None)
        if not callable(tokenizer):
            return [part for part in re.split(r"\s+", source.strip()) if part], []
        try:
            pieces = tokenizer(source)
        except Exception as exc:
            return [source], [f"{kind} segmentation failed: {exc}"]
        return [str(piece) for piece in pieces if str(piece).strip()], []

    def pronounce_thai_chunk(self, source: str) -> EngineResult:
        """Pronounce a chunk, retrying independently segmented pieces on failure."""
        result = EngineResult(source=source)
        if not source.strip():
            return result
        try:
            raw = self._call_tltk(source)
            if raw and not self._looks_truncated(source, raw):
                result.raw_ipa = raw
                return result
            result.warnings.append("TH_ENGINE_TRUNCATED" if raw else "TH_ENGINE_EMPTY")
        except Exception as exc:
            result.warnings.append(f"TH_ENGINE_EXCEPTION: {exc}")

        result.used_fallback = True
        syllables = self._segment_units(source, "syllable_tokenize")
        if isinstance(syllables, tuple):
            syllables, segmentation_warnings = syllables
            result.warnings.extend(segmentation_warnings)
        pieces = syllables
        if len(pieces) <= 1 or pieces == [source]:
            words = self._segment_units(source, "word_tokenize")
            if isinstance(words, tuple):
                words, segmentation_warnings = words
                result.warnings.extend(segmentation_warnings)
            pieces = words
        recovered: list[str] = []
        for piece in pieces:
            try:
                raw_piece = self._call_tltk(piece)
            except Exception as exc:
                result.warnings.append(f"TH_ENGINE_EXCEPTION: {piece!r}: {exc}")
                raw_piece = ""
            if raw_piece and not self._looks_truncated(piece, raw_piece):
                recovered.append(raw_piece)
            else:
                result.unrecovered.append(piece)
                result.warnings.append(
                    "TH_ENGINE_EMPTY: " + repr(piece)
                    if not raw_piece
                    else "TH_ENGINE_TRUNCATED: " + repr(piece)
                )
        result.raw_ipa = " ".join(recovered)
        if result.unrecovered:
            result.warnings.append(
                "TH_UNRECOVERED_WORD: "
                + ", ".join(repr(piece) for piece in result.unrecovered)
            )
        return result


__all__ = ["EngineResult", "ThaiEngine", "ThaiG2PError"]
