"""Source-aligned native Russian G2P frontend."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from kokorog2p.base import G2PBase
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions, tokenize_with_offsets

from .accent import (
    RussianAccentuator,
    make_accentuator,
    normalize_explicit_stress,
)
from .alignment import TextAlignment, align_accented_text
from .engine import RussianEspeakEngine
from .model_profile import (
    TARGET_MODEL,
    transform_russian_ipa,
    validate_russian_symbols,
)
from .orthoepy import apply_orthoepy

_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LATIN_RE = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class RussianAnalysis:
    source: str
    accented: str
    phonemes: str
    applied_rules: tuple[str, ...] = ()
    invalid_symbols: tuple[str, ...] = ()


class RussianG2P(G2PBase):
    """Russian frontend with contextual stress and stock Kokoro labels."""

    aliases = frozenset({"ru", "ru-ru", "rus", "russian"})

    def __init__(
        self,
        language: str = "ru-ru",
        *,
        accentuator: RussianAccentuator | Literal["auto", "none"] = "auto",
        omograph_model_size: str = "turbo3.1",
        use_stress_dictionary: bool = True,
        espeak_data: str | None = None,
        strict_stress: bool = True,
        reduction: bool = True,
        preserve_stress: bool = True,
        use_cli: bool = False,
        strict: bool = True,
        version: str = "1.0",
        latin_policy: Literal["preserve", "english", "drop"] = "preserve",
        engine: RussianEspeakEngine | Any | None = None,
    ) -> None:
        normalized = language.lower().replace("_", "-")
        if normalized not in self.aliases:
            raise ValueError(f"Unsupported Russian language code: {language!r}")
        if version != TARGET_MODEL:
            raise ValueError("RussianG2P supports frontend version '1.0'.")
        if latin_policy not in {"preserve", "english", "drop"}:
            raise ValueError("latin_policy must be 'preserve', 'english', or 'drop'.")
        super().__init__(language="ru-ru", use_cli=use_cli, strict=strict)
        self.version = version
        self.reduction = reduction
        self.preserve_stress = preserve_stress
        self.latin_policy = latin_policy
        self.strict_stress = strict_stress
        self.espeak_data = espeak_data
        self._accentuator_spec = accentuator
        self._accentuator_model_size = omograph_model_size
        self._use_stress_dictionary = use_stress_dictionary
        if isinstance(accentuator, str):
            self._accentuator = None
            self._accentuator_initialized = False
        else:
            self._accentuator = accentuator
            self._accentuator_initialized = True
        self._engine = engine
        self.warnings: list[str] = []

    @property
    def accentuator(self) -> RussianAccentuator:
        if not self._accentuator_initialized:
            self._accentuator = make_accentuator(
                self._accentuator_spec,
                model_size=self._accentuator_model_size,
                use_stress_dictionary=self._use_stress_dictionary,
                strict=self.strict,
            )
            self._accentuator_initialized = True
        return self._accentuator

    @property
    def espeak_engine(self) -> RussianEspeakEngine | Any:
        if self._engine is None:
            self._engine = RussianEspeakEngine(
                data_path=self.espeak_data,
                use_cli=self.use_cli,
                strict_stress=self.strict_stress,
            )
        return self._engine

    def accentuate(self, text: str) -> str:
        """Return sentence-level text with normalized combining-acute stress."""
        result = self.accentuator.accentuate(text)
        return normalize_explicit_stress(result, strict=self.strict)

    def _alignment(self, text: str, accented: str | None = None) -> TextAlignment:
        processed = (
            self.accentuate(text)
            if accented is None
            else normalize_explicit_stress(accented, strict=self.strict)
        )
        return align_accented_text(
            text,
            processed,
            adapter_name=getattr(
                self.accentuator, "name", type(self.accentuator).__name__
            ),
        )

    @staticmethod
    def _is_punctuation(text: str) -> bool:
        return bool(text) and not any(char.isalnum() for char in text)

    @staticmethod
    def _is_cyrillic(text: str) -> bool:
        return bool(_CYRILLIC_RE.search(text))

    @staticmethod
    def _is_latin(text: str) -> bool:
        return bool(text) and bool(
            _LATIN_RE.fullmatch(text.replace("'", "").replace("-", ""))
        )

    def _word_analysis(self, source: str, accented: str) -> RussianAnalysis:
        orthoepy = apply_orthoepy(accented)
        raw = self.espeak_engine.phonemize_marked(orthoepy.rewritten)
        phonemes = transform_russian_ipa(raw, reduction=self.reduction)
        invalid = tuple(
            validate_russian_symbols(
                phonemes,
                source_token=source,
                raw_ipa=raw,
                strict=self.strict,
            )
        )
        return RussianAnalysis(
            source=source,
            accented=accented,
            phonemes=phonemes,
            applied_rules=orthoepy.applied_rules,
            invalid_symbols=invalid,
        )

    def _token(
        self,
        source: str,
        whitespace: str,
        start: int,
        end: int,
        alignment: TextAlignment,
    ) -> GToken:
        if self._is_punctuation(source):
            token = GToken(
                text=source,
                tag="PUNCT",
                whitespace=whitespace,
                phonemes=normalize_punctuation(source),
            )
            token.set("source_kind", "PUNCTUATION")
        elif self._is_latin(source):
            token = GToken(text=source, tag="LATIN", whitespace=whitespace)
            token.set("source_kind", "LATIN_PRESERVED")
            if self.latin_policy == "drop":
                token.tag = "DROP"
                token.set("drop", True)
                token.set("source_kind", "LATIN_DROPPED")
        else:
            accented = alignment.accented_for_source(start, end)
            analysis = self._word_analysis(source, accented)
            token = GToken(
                text=source,
                tag="X",
                whitespace=whitespace,
                phonemes=analysis.phonemes or None,
                rating="espeak" if analysis.phonemes else None,
            )
            token.set(
                "source_kind", "RUSSIAN_WORD" if self._is_cyrillic(source) else "OTHER"
            )
            token.set("accented_text", accented)
            token.set("orthoepy_rules", analysis.applied_rules)
            if analysis.invalid_symbols:
                token.set("invalid_symbols", analysis.invalid_symbols)
                self.warnings.append(
                    f"Russian output for {source!r} contains unsupported symbols: "
                    f"{''.join(analysis.invalid_symbols)}"
                )
        token.set("char_start", start)
        token.set("char_end", end)
        return token

    def _tokens_from_alignment(
        self, text: str, alignment: TextAlignment
    ) -> list[GToken]:
        spans = tokenize_with_offsets(text, lang="ru-ru", keep_punct=True)
        tokens: list[GToken] = []
        for index, span in enumerate(spans):
            next_start = (
                spans[index + 1].char_start if index + 1 < len(spans) else len(text)
            )
            whitespace = text[span.char_end : next_start]
            tokens.append(
                self._token(
                    span.text, whitespace, span.char_start, span.char_end, alignment
                )
            )
        ensure_gtoken_positions(tokens, text)
        return tokens

    def phonemize_accented(self, text: str) -> list[GToken]:
        """Phonemize caller-supplied combining-acute stress without RUAccent."""
        if not text:
            return []
        alignment = self._alignment(text, text)
        return self._tokens_from_alignment(text, alignment)

    def analyze(self, text: str) -> RussianAnalysis:
        alignment = self._alignment(text)
        words = [
            span for span in tokenize_with_offsets(text, lang="ru-ru", keep_punct=False)
        ]
        analyses = [
            self._word_analysis(
                span.text,
                alignment.accented_for_source(span.char_start, span.char_end),
            )
            for span in words
            if self._is_cyrillic(span.text)
        ]
        return RussianAnalysis(
            source=text,
            accented=alignment.accented,
            phonemes=" ".join(item.phonemes for item in analyses),
            applied_rules=tuple(
                rule for item in analyses for rule in item.applied_rules
            ),
        )

    def __call__(self, text: str) -> list[GToken]:
        self.warnings = []
        if not text:
            return []
        alignment = self._alignment(text)
        return self._tokens_from_alignment(text, alignment)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        del tag
        if not word or not self._is_cyrillic(word):
            return None
        alignment = self._alignment(word)
        return self._word_analysis(word, alignment.accented).phonemes or None

    def capabilities(self) -> dict[str, object]:
        return {
            "language": "ru-ru",
            "native": True,
            "model": TARGET_MODEL,
            "contextual_stress": self._accentuator_spec != "none",
            "explicit_stress": True,
            "source_aligned": True,
            "reduction": self.reduction,
            "latin_policy": self.latin_policy,
        }

    def __repr__(self) -> str:
        return (
            f"RussianG2P(language={self.language!r}, model={TARGET_MODEL!r}, "
            f"accentuator={self._accentuator!r})"
        )
