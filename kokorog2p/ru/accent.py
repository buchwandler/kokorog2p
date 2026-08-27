"""Lazy Russian stress adapters and explicit-stress normalization."""

from __future__ import annotations

import importlib
import unicodedata
from pathlib import Path
from typing import Any, Literal, Protocol

RUSSIAN_VOWELS = frozenset("аеёиоуыэюяАЕЁИОУЫЭЮЯ")
COMBINING_ACUTE = "\u0301"


class RussianAccentuator(Protocol):
    """Small protocol implemented by contextual and test accentuators."""

    def accentuate(self, text: str) -> str: ...


class RussianAccentError(ValueError):
    """Raised for malformed or unavailable Russian stress annotation."""


def normalize_explicit_stress(
    text: str,
    *,
    strict: bool = True,
) -> str:
    """Normalize acute accents and legacy ``+vowel`` stress to combining acute."""
    text = unicodedata.normalize("NFD", text).replace("´", COMBINING_ACUTE)
    result: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "+" and index + 1 < len(text) and text[index + 1] in RUSSIAN_VOWELS:
            result.extend((text[index + 1], COMBINING_ACUTE))
            index += 2
            continue
        if char == COMBINING_ACUTE and (not result or result[-1] not in RUSSIAN_VOWELS):
            if strict:
                raise RussianAccentError(
                    "Combining acute must follow a Russian vowel at character "
                    f"{index}: {text[max(0, index - 8) : index + 8]!r}"
                )
            index += 1
            continue
        result.append(char)
        index += 1
    return unicodedata.normalize("NFC", "".join(result))


class NoAccentAdapter:
    """Preserve caller-provided stress without contextual model inference."""

    name = "none"

    def __init__(self, *, strict: bool = True) -> None:
        self.strict = strict

    def accentuate(self, text: str) -> str:
        return normalize_explicit_stress(text, strict=self.strict)

    def __repr__(self) -> str:
        return f"NoAccentAdapter(strict={self.strict})"


class RuAccentAdapter:
    """Lazily load RUAccent through its public API when first used."""

    name = "ruaccent"

    def __init__(
        self,
        *,
        model_size: str = "turbo3.1",
        use_stress_dictionary: bool = True,
        workdir: str | Path | None = None,
        strict: bool = True,
    ) -> None:
        self.model_size = model_size
        self.use_stress_dictionary = use_stress_dictionary
        self.workdir = Path(workdir) if workdir is not None else None
        self.strict = strict
        self._model: Any | None = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _load(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            module = importlib.import_module("ruaccent")
        except ImportError as exc:
            raise RussianAccentError(
                "Russian contextual stress requires the optional 'ruaccent' package. "
                "Install it with: pip install 'kokorog2p[ru]'"
            ) from exc
        try:
            accent_class = module.RUAccent
            model = accent_class()
            load_kwargs: dict[str, Any] = {
                "omograph_model_size": self.model_size,
                "use_dictionary": self.use_stress_dictionary,
            }
            if self.workdir is not None:
                load_kwargs["workdir"] = str(self.workdir)
            model.load(**load_kwargs)
        except Exception as exc:
            raise RussianAccentError(
                "Could not load RUAccent model artifacts. Check the selected model "
                f"({self.model_size!r}), optional dependencies, and model cache. "
                f"Original error: {exc}"
            ) from exc
        self._model = model
        return model

    def accentuate(self, text: str) -> str:
        model = self._load()
        try:
            if hasattr(model, "process_all"):
                output = model.process_all(text)
            else:
                output = model.process(text)
        except Exception as exc:
            raise RussianAccentError(f"RUAccent failed for {text!r}: {exc}") from exc
        if not isinstance(output, str):
            raise RussianAccentError("RUAccent returned a non-string result")
        return normalize_explicit_stress(output, strict=self.strict)

    def __repr__(self) -> str:
        return (
            f"RuAccentAdapter(model_size={self.model_size!r}, "
            f"use_stress_dictionary={self.use_stress_dictionary}, loaded={self.loaded})"
        )


def make_accentuator(
    accentuator: RussianAccentuator | Literal["auto", "none"],
    *,
    model_size: str,
    use_stress_dictionary: bool,
    strict: bool,
) -> RussianAccentuator:
    """Construct a configured adapter without importing RUAccent for ``none``."""
    if accentuator == "none":
        return NoAccentAdapter(strict=strict)
    if accentuator == "auto":
        return RuAccentAdapter(
            model_size=model_size,
            use_stress_dictionary=use_stress_dictionary,
            strict=strict,
        )
    return accentuator
