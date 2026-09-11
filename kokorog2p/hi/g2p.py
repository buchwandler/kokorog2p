"""Source-aligned Hindi G2P backed by the eSpeak-NG hi voice."""

from __future__ import annotations

from typing import Any

from kokorog2p.espeak_g2p import EspeakOnlyG2P

from .model_profile import (
    TARGET_MODEL,
    transform_hindi_ipa,
    validate_hindi_symbols,
)


class HindiG2P(EspeakOnlyG2P):
    """Hindi frontend that preserves raw Hindi eSpeak IPA semantics."""

    aliases = frozenset({"hi", "hi-in", "hin", "hindi"})

    def __init__(
        self,
        language: str = "hi-in",
        *,
        strict: bool = True,
        version: str = TARGET_MODEL,
        use_cli: bool = False,
        **kwargs: Any,
    ) -> None:
        if kwargs:
            names = ", ".join(sorted(kwargs))
            raise TypeError(f"Unsupported HindiG2P options: {names}")
        normalized = language.lower().replace("_", "-")
        if normalized not in self.aliases:
            raise ValueError(f"Unsupported Hindi language code: {language!r}")
        if version != TARGET_MODEL:
            raise ValueError("HindiG2P supports frontend version '1.0'.")
        super().__init__(
            language="hi-in",
            strict=strict,
            version=version,
            use_cli=use_cli,
        )

    def _validation_text(self) -> str:
        return "नमस्ते"

    def _validate_backend(self) -> None:
        """Verify that the eSpeak-NG installation exposes voice hi."""
        if self._espeak_backend is None:
            raise RuntimeError("Backend not initialized")
        try:
            raw = self._espeak_backend.phonemize(
                self._validation_text(), convert_to_kokoro=False
            )
            if raw == "":
                raise RuntimeError("the validation word produced no phonemes")
            normalized = transform_hindi_ipa(raw)
            validate_hindi_symbols(
                normalized,
                source_token=self._validation_text(),
                raw_ipa=raw,
            )
        except Exception as error:
            raise RuntimeError(
                "Hindi requires an eSpeak-NG installation/data set that provides "
                "voice 'hi'. "
                f"Original error: {error}"
            ) from error

    def _normalize_and_validate(self, raw: str, source_token: str) -> str:
        if not raw:
            raise RuntimeError(
                f"eSpeak-NG returned empty output for Hindi token {source_token!r}."
            )
        phonemes = transform_hindi_ipa(raw)
        invalid = validate_hindi_symbols(
            phonemes,
            source_token=source_token,
            raw_ipa=raw,
            strict=self.strict,
        )
        if invalid:
            return ""
        return phonemes

    def _phonemize_word(self, word: str) -> str:
        raw = self.espeak_backend.word_phonemes(word, convert_to_kokoro=False)
        return self._normalize_and_validate(raw, word)

    def _phonemize_text(self, text: str) -> str:
        raw = self.espeak_backend.phonemize(text, convert_to_kokoro=False)
        return self._normalize_and_validate(raw, text)

    def get_target_model(self) -> str:
        return TARGET_MODEL

    def capabilities(self) -> dict[str, object]:
        return {
            "language": "hi-in",
            "native": True,
            "engine": "espeak-ng",
            "version": self.version,
            "target_model": TARGET_MODEL,
            "runtime_lexicon": False,
            "source_aligned": True,
            "raw_ipa": True,
        }

    def __repr__(self) -> str:
        return f"HindiG2P(language={self.language!r}, model={TARGET_MODEL!r})"
