"""Lexphon-backed native Russian G2P frontend."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from kokorog2p.base import G2PBase
from kokorog2p.lexicons.lexphon_backend import LexphonBackend
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.ru.model_profile import (
    TARGET_MODEL,
    normalize_russian_lexicon_ipa,
    validate_russian_symbols,
)
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions, tokenize_with_offsets

_CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
_LATIN_RE = re.compile(r"[A-Za-z]+")
_STRESS_RE = re.compile(r"[ˈˌ]")


class RussianG2PError(ValueError):
    """Actionable native Russian pronunciation error."""


@dataclass(frozen=True)
class RussianAnalysis:
    source: str
    accented: str
    phonemes: str
    applied_rules: tuple[str, ...] = ()
    invalid_symbols: tuple[str, ...] = ()


class RussianG2P(G2PBase):
    """Russian frontend using the provisioned ``ru:lexhint`` dictionary."""

    aliases = frozenset({"ru", "ru-ru", "rus", "russian"})

    def __init__(
        self,
        language: str = "ru-ru",
        *,
        reduction: bool = False,
        preserve_stress: bool = True,
        use_cli: bool = False,
        strict: bool = True,
        version: str = "1.0",
        latin_policy: Literal["preserve", "english", "drop"] = "preserve",
        lexicons: Sequence[str] | None = None,
        store: object | None = None,
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
        self.warnings: list[str] = []
        self.lexicons = ("lexhint",) if lexicons is None else tuple(lexicons)
        self.store = store
        if self.lexicons:
            self._lexphon = LexphonBackend("ru-ru", self.lexicons, store=store)
        else:
            self._lexphon = None

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

    @staticmethod
    def _lookup_text(source: str) -> str:
        return _STRESS_RE.sub("", unicodedata.normalize("NFC", source))

    def _word_analysis(self, source: str) -> RussianAnalysis:
        if self._lexphon is None:
            return RussianAnalysis(source, source, "")
        lookup = self._lexphon.lookup(self._lookup_text(source))
        if lookup is None or not lookup.known or lookup.pronunciation is None:
            if self.strict:
                raise RussianG2PError(
                    f"Russian word {source!r} is absent from "
                    "lexicon 'lexhint' (ru:lexhint)."
                )
            self.warnings.append(f"Russian word {source!r} is unresolved.")
            return RussianAnalysis(source, source, "")
        phonemes = normalize_russian_lexicon_ipa(
            lookup.pronunciation, preserve_stress=self.preserve_stress
        )
        invalid = tuple(
            validate_russian_symbols(
                phonemes,
                source_token=source,
                raw_ipa=lookup.pronunciation,
                strict=self.strict,
            )
        )
        if invalid:
            self.warnings.append(
                f"Russian output for {source!r} contains unsupported "
                f"symbols: {''.join(invalid)}"
            )
            phonemes = ""
        return RussianAnalysis(source, source, phonemes, invalid_symbols=invalid)

    def _token(self, source: str, whitespace: str, start: int, end: int) -> GToken:
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
            analysis = self._word_analysis(source)
            token = GToken(
                text=source,
                tag="X",
                whitespace=whitespace,
                phonemes=analysis.phonemes or None,
                rating="5" if analysis.phonemes else None,
            )
            token.set(
                "source_kind",
                "RUSSIAN_WORD" if self._is_cyrillic(source) else "OTHER",
            )
            token.set("source", "lexicon")
            token.set("lexicon_id", "ru:lexhint")
            if analysis.invalid_symbols:
                token.set("invalid_symbols", analysis.invalid_symbols)
        token.set("char_start", start)
        token.set("char_end", end)
        return token

    def __call__(self, text: str) -> list[GToken]:
        self.warnings = []
        if not text:
            return []
        spans = tokenize_with_offsets(text, lang="ru-ru", keep_punct=True)
        tokens: list[GToken] = []
        for index, span in enumerate(spans):
            next_start = (
                spans[index + 1].char_start if index + 1 < len(spans) else len(text)
            )
            tokens.append(
                self._token(
                    span.text,
                    text[span.char_end : next_start],
                    span.char_start,
                    span.char_end,
                )
            )
        ensure_gtoken_positions(tokens, text)
        return tokens

    def phonemize_accented(self, text: str) -> list[GToken]:
        return self(text)

    def analyze(self, text: str) -> RussianAnalysis:
        tokens = self(text)
        phonemes = " ".join(token.phonemes or "" for token in tokens if token.is_word)
        return RussianAnalysis(text, text, phonemes)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        del tag
        if not word or not self._is_cyrillic(word):
            return None
        return self._word_analysis(word).phonemes or None

    def capabilities(self) -> dict[str, object]:
        return {
            "language": "ru-ru",
            "native": True,
            "model": TARGET_MODEL,
            "lexphon": True,
            "lexicon_segmentation": False,
            "preserve_stress": self.preserve_stress,
            "reduction": self.reduction,
            "latin_policy": self.latin_policy,
        }

    def close(self) -> None:
        if self._lexphon is not None:
            self._lexphon.close()

    def __repr__(self) -> str:
        return f"RussianG2P(language={self.language!r}, model={TARGET_MODEL!r})"
