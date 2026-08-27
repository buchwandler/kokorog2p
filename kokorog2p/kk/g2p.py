"""Source-aligned Kazakh G2P backed by the eSpeak-NG kk voice."""

from __future__ import annotations

from typing import Any

from kokorog2p.espeak_g2p import EspeakOnlyG2P

from .model_profile import (
    TARGET_MODEL,
    KazakhVocabularyError,
    transform_kazakh_ipa,
    validate_kazakh_symbols,
)


class KazakhG2P(EspeakOnlyG2P):
    """Kazakh frontend that preserves raw non-English eSpeak IPA semantics."""

    aliases = frozenset({"kk", "kk-kz", "kaz", "kazakh"})

    def __init__(
        self,
        language: str = "kk",
        *,
        strict: bool = True,
        version: str = TARGET_MODEL,
        use_cli: bool = False,
        **kwargs: Any,
    ) -> None:
        if kwargs:
            names = ", ".join(sorted(kwargs))
            raise TypeError(f"Unsupported KazakhG2P options: {names}")
        normalized = language.lower().replace("_", "-")
        if normalized not in self.aliases:
            raise ValueError(f"Unsupported Kazakh language code: {language!r}")
        if version != TARGET_MODEL:
            raise ValueError("KazakhG2P supports frontend version '1.0'.")
        super().__init__(language="kk", strict=strict, version=version, use_cli=use_cli)

    def _validation_text(self) -> str:
        return "сәлем"

    def _validate_backend(self) -> None:
        """Verify that the configured eSpeak-NG installation exposes voice kk."""
        if self._espeak_backend is None:
            raise RuntimeError("Backend not initialized")
        try:
            raw = self._espeak_backend.phonemize(
                self._validation_text(), convert_to_kokoro=False
            )
        except Exception as error:
            raise RuntimeError(
                "Kazakh requires an eSpeak-NG installation/data set that provides "
                "voice 'kk'. "
                f"Original error: {error}"
            ) from error
        if not raw:
            raise RuntimeError(
                "Kazakh requires an eSpeak-NG installation/data set that provides "
                "voice 'kk'; "
                "the validation word produced no phonemes."
            )

    def _normalize_and_validate(self, raw: str, source_token: str) -> str:
        if not raw:
            raise RuntimeError(
                f"eSpeak-NG returned empty output for Kazakh token {source_token!r}."
            )
        phonemes = transform_kazakh_ipa(raw)
        invalid = validate_kazakh_symbols(
            phonemes,
            source_token=source_token,
            raw_ipa=raw,
            strict=self.strict,
        )
        if invalid:
            raise KazakhVocabularyError(invalid[0], source_token, raw, phonemes)
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
            "language": "kk",
            "native": True,
            "engine": "espeak-ng",
            "version": self.version,
            "target_model": TARGET_MODEL,
            "runtime_lexicon": False,
            "source_aligned": True,
            "raw_ipa": True,
        }

    def __repr__(self) -> str:
        return f"KazakhG2P(language={self.language!r}, model={TARGET_MODEL!r})"
