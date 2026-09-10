#!/usr/bin/env python3
"""Backward-compatible entry point for the shared reference benchmark."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from benchmarks.benchmark_reference import main as reference_main


class KokoroG2PWrapper:
    """Compatibility adapter retained for historical spacing tests and callers."""

    def __init__(self, language: str = "en-us") -> None:
        from kokorog2p import get_g2p

        self.language = language
        self.g2p = get_g2p(language=language, use_espeak_fallback=True, use_spacy=True)
        self.version = self._get_version()

    @staticmethod
    def _get_version() -> str:
        import kokorog2p

        return str(getattr(kokorog2p, "__version__", "unknown"))

    def phonemize(self, text: str) -> tuple[str, list[Any]]:
        tokens = self.g2p(text)
        output: list[str] = []
        for token in tokens:
            if token.phonemes:
                output.append(token.phonemes)
            elif token.text.strip():
                output.append(f"[{token.text}]")
            if token.whitespace:
                output.append(" ")
        return "".join(output).strip(), tokens

    def phonemize_clean(self, text: str) -> str:
        tokens = self.g2p(text)
        output: list[str] = []
        for token in tokens:
            if token.phonemes and token.phonemes != "❓":
                output.append(token.phonemes)
                if token.whitespace:
                    output.append(" ")
        return "".join(output).strip()


class MisakiWrapper:
    """Compatibility adapter for callers that still instantiate the old wrapper."""

    def __init__(self, language: str = "en-us") -> None:
        from benchmarks.reference.providers import HexgradEnglishMisakiProvider

        self.provider = HexgradEnglishMisakiProvider(british=language == "en-gb")
        self.language = language
        self.version = self.provider.metadata.package_version

    def phonemize(self, text: str) -> tuple[str, list[Any]]:
        output = self.provider.phonemize(
            text, case_id="compat", language=self.language, model="1.0"
        )
        if output.error:
            raise RuntimeError(output.error.message)
        return output.phonemes, []


def main(argv: list[str] | None = None) -> int:
    return reference_main(
        argv,
        default_reference="hexgrad-en-us-v1",
        default_candidate="en-us-default",
    )


if __name__ == "__main__":
    raise SystemExit(main())
