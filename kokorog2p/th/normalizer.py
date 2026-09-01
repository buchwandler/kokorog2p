"""Deprecated Spokenform-backed Thai normalization compatibility surface."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterable, Iterator

from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.types import TextReplacement


class ThaiNormalizer:
    """Compatibility adapter delegating Thai semantics to Spokenform.

    The class remains for callers of the historical direct G2P API. Semantic
    replacements and source coordinates come from Spokenform; this adapter only
    retains Thai model-input sanitation for unsupported symbols and Latin accents.
    """

    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.diagnostics: list[dict[str, str]] = []

    @staticmethod
    def _fold_latin_accents(text: str) -> str:
        output: list[str] = []
        for char in text:
            if char.isascii() and char.isalpha():
                output.append(char)
                continue
            if char.isalpha() and "LATIN" in unicodedata.name(char, ""):
                output.extend(
                    part
                    for part in unicodedata.normalize("NFKD", char)
                    if not unicodedata.combining(part)
                )
            else:
                output.append(char)
        return "".join(output)

    def _drop_unsupported(self, text: str) -> str:
        kept: list[str] = []
        dropped: list[str] = []
        for char in text:
            category = unicodedata.category(char)
            if (
                category.startswith("C")
                and char not in "\n\t\r"
                or category == "So"
                and not ("THAI" in unicodedata.name(char, ""))
            ):
                dropped.append(char)
            else:
                kept.append(char)
        if dropped:
            unique = "".join(dict.fromkeys(dropped))
            warning = f"TH_UNSUPPORTED_SOURCE_SYMBOL: dropped {unique!r}"
            self.warnings.append(warning)
            self.diagnostics.append(
                {"kind": "TH_UNSUPPORTED_SOURCE_SYMBOL", "symbols": unique}
            )
        return "".join(kept)

    def normalize(self, text: str) -> str:
        """Sanitize prepared Thai model input without semantic expansion."""
        self.warnings = []
        self.diagnostics = []
        result = self._fold_latin_accents(normalize_punctuation(text))
        result = self._drop_unsupported(result)
        return " ".join(result.split())

    def __call__(self, text: str) -> str:
        return self.normalize(text)

    def normalize_token(self, text: str, **_: object) -> str:
        """Sanitize one already-prepared token without semantic expansion."""
        result = self._fold_latin_accents(normalize_punctuation(text))
        return self._drop_unsupported(result)

    def iter_structured_replacements(
        self, text: str, *, protected_spans: Iterable[tuple[int, int]] = ()
    ) -> Iterator[TextReplacement]:
        """Return no semantic replacements from the Thai G2P layer."""
        del text, protected_spans
        return iter(())

    def normalize_for_g2p(self, text: str) -> str:
        """Sanitize text that has already received Spokenform semantics."""
        return self.normalize_token(text)


__all__ = ["ThaiNormalizer"]
