"""Native source-aligned Arabic MSA frontend for KokoroG2P."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import Any

from kokorog2p.ar.diacritizer import (
    ArabicDiacritizer,
    CamelMLEDiacritizer,
    DiacritizerMode,
    NoneDiacritizer,
)
from kokorog2p.ar.model_profile import (
    TARGET_MODEL,
    clean_espeak_output,
    validate_nabra_symbols,
)
from kokorog2p.base import G2PBase
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions, tokenize_with_offsets

_ASCII_LATIN_RE = re.compile(r"[A-Za-z]+(?:['’-][A-Za-z]+)*")
_CITATION_RE = re.compile(r"\[[0-9]+(?:\s*[,;]\s*[0-9]+)*\]")


class ArabicG2P(G2PBase):
    """Source-preserving Arabic MSA frontend targeting Nabra."""

    preserve_source_punctuation = True

    def __init__(
        self,
        language: str = "ar",
        *,
        version: str = "1.0",
        model_profile: str = TARGET_MODEL,
        diacritizer: DiacritizerMode | ArabicDiacritizer = "auto",
        latin_policy: str = "drop",
        citation_policy: str = "suppress",
        strict_diacritizer: bool = False,
        use_cli: bool = False,
        strict: bool = True,
        **_: Any,
    ) -> None:
        super().__init__(language=language, use_cli=use_cli, strict=strict)
        if version not in ("1.0",):
            raise ValueError("ArabicG2P supports frontend version '1.0'.")
        if model_profile not in {TARGET_MODEL, "nabra", "nabra-82m"}:
            raise ValueError(f"Unsupported Arabic model profile: {model_profile!r}")
        if latin_policy not in {"drop", "keep"}:
            raise ValueError("latin_policy must be 'drop' or 'keep'.")
        if citation_policy not in {"suppress", "keep"}:
            raise ValueError("citation_policy must be 'suppress' or 'keep'.")
        if isinstance(diacritizer, str) and diacritizer not in {
            "auto",
            "none",
            "camel-tools",
        }:
            raise ValueError(
                "diacritizer must be 'auto', 'none', 'camel-tools', or an adapter."
            )
        self.version = version
        self.model_profile = TARGET_MODEL
        self.latin_policy = latin_policy
        self.citation_policy = citation_policy
        self.strict_diacritizer = strict_diacritizer
        self._diacritizer_spec = diacritizer
        self._diacritizer: ArabicDiacritizer | None = None
        self._espeak_backend: Any | None = None
        self.warnings: list[str] = []

    def get_target_model(self) -> str:
        """Return the vocabulary profile required by the target acoustic model."""
        return self.model_profile

    def capabilities(self) -> dict[str, bool]:
        """Describe source and model behavior used by the public pipeline."""
        return {
            "preserve_source_punctuation": True,
            "source_sensitive_punctuation": True,
            "raw_ipa": True,
        }

    @property
    def espeak_backend(self) -> Any:
        if self._espeak_backend is None:
            from kokorog2p.backends.espeak import EspeakBackend

            self._espeak_backend = EspeakBackend(
                language="ar",
                with_stress=True,
                use_cli=self.use_cli,
            )
        return self._espeak_backend

    def _get_diacritizer(self) -> ArabicDiacritizer:
        if self._diacritizer is not None:
            return self._diacritizer
        spec = self._diacritizer_spec
        if not isinstance(spec, str):
            self._diacritizer = spec
        elif spec == "none":
            self._diacritizer = NoneDiacritizer()
        elif spec == "camel-tools":
            self._diacritizer = CamelMLEDiacritizer()
        else:
            self._diacritizer = CamelMLEDiacritizer()
        return self._diacritizer

    def _diacritize(self, tokens: Sequence[str]) -> list[str]:
        if not tokens:
            return []
        try:
            enriched = self._get_diacritizer().diacritize_tokens(tokens)
        except Exception:
            if self._diacritizer_spec == "auto" and not self.strict_diacritizer:
                self.warnings.append(
                    "CAMeL MLE diacritizer unavailable; using source Arabic "
                    "without added diacritics."
                )
                return list(tokens)
            raise
        if len(enriched) != len(tokens):
            raise ValueError(
                "Arabic diacritizer returned a different number of tokens "
                f"({len(enriched)}) than requested ({len(tokens)})."
            )
        return enriched

    @staticmethod
    def _is_arabic_word(text: str) -> bool:
        return any("\u0600" <= char <= "\u06ff" for char in text) and any(
            char.isalnum() for char in text
        )

    @staticmethod
    def _is_punctuation(text: str) -> bool:
        return bool(text) and all(
            unicodedata.category(char)[0] in {"P", "S"} for char in text
        )

    def _source_drop_kind(
        self, text: str, citation_spans: Sequence[tuple[int, int]], start: int, end: int
    ) -> str | None:
        if self.citation_policy == "suppress" and any(
            start >= citation_start and end <= citation_end
            for citation_start, citation_end in citation_spans
        ):
            return "AR_CITATION"
        if self.latin_policy == "drop" and _ASCII_LATIN_RE.fullmatch(text):
            return "ASCII_LATIN_DROPPED"
        return None

    def __call__(self, text: str) -> list[GToken]:
        if not text:
            self.warnings = []
            return []
        self.warnings = []
        token_spans = tokenize_with_offsets(text, lang="ar", keep_punct=True)
        citation_spans = [match.span() for match in _CITATION_RE.finditer(text)]
        arabic_indices: list[int] = []
        arabic_words: list[str] = []
        for index, span in enumerate(token_spans):
            if self._source_drop_kind(
                span.text, citation_spans, span.char_start, span.char_end
            ):
                continue
            if self._is_arabic_word(span.text):
                arabic_indices.append(index)
                arabic_words.append(span.text)
        latin_dropped = sum(
            self.latin_policy == "drop"
            and _ASCII_LATIN_RE.fullmatch(span.text) is not None
            for span in token_spans
        )
        if latin_dropped:
            self.warnings.append(
                f"Arabic frontend skipped {latin_dropped} ASCII-Latin span(s) "
                "under latin_policy='drop'."
            )
        if self.citation_policy == "suppress" and citation_spans:
            self.warnings.append(
                f"Arabic frontend skipped {len(citation_spans)} square-bracket "
                "citation span(s)."
            )
        diacritized = self._diacritize(arabic_words)
        diacritized_by_index = dict(zip(arabic_indices, diacritized, strict=True))

        tokens: list[GToken] = []
        for index, span in enumerate(token_spans):
            next_start = (
                token_spans[index + 1].char_start
                if index + 1 < len(token_spans)
                else len(text)
            )
            whitespace = text[span.char_end : next_start]
            drop_kind = self._source_drop_kind(
                span.text, citation_spans, span.char_start, span.char_end
            )
            if drop_kind is not None:
                token = GToken(text=span.text, tag="DROP", whitespace=whitespace)
                token.set("drop", True)
                token.set("source_kind", drop_kind)
            elif self._is_punctuation(span.text):
                punctuation = normalize_punctuation(span.text)
                token = GToken(
                    text=span.text,
                    tag="PUNCT",
                    whitespace=whitespace,
                    phonemes=punctuation,
                )
                token.set("source_kind", "PUNCTUATION")
            else:
                source_text = diacritized_by_index.get(index, span.text)
                phonemes = self._phonemize_word(source_text)
                token = GToken(
                    text=span.text,
                    tag="X",
                    whitespace=whitespace,
                    phonemes=phonemes,
                    rating="espeak" if phonemes else None,
                )
                token.set(
                    "source_kind",
                    "ARABIC_WORD" if self._is_arabic_word(span.text) else "OTHER",
                )
            token.set("char_start", span.char_start)
            token.set("char_end", span.char_end)
            tokens.append(token)
        ensure_gtoken_positions(tokens, text)
        if self.warnings:
            self.warnings = list(dict.fromkeys(self.warnings))
        return tokens

    def _phonemize_word(self, word: str) -> str | None:
        try:
            raw = self.espeak_backend.phonemize(
                word,
                convert_to_kokoro=False,
                remove_punctuation=False,
            )
        except Exception as exc:
            if self.strict:
                raise RuntimeError(
                    f"ArabicG2P failed to phonemize {word!r}: {exc}"
                ) from exc
            self.warnings.append(f"ArabicG2P failed to phonemize {word!r}: {exc}")
            return None
        cleaned = clean_espeak_output(raw)
        valid, invalid = validate_nabra_symbols(cleaned)
        if not valid:
            symbols = "".join(sorted(set(invalid)))
            message = f"Nabra Arabic frontend produced unsupported symbols: {symbols}"
            if self.strict:
                raise ValueError(message)
            self.warnings.append(message)
        return cleaned or None

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        return self._phonemize_word(word)

    def __repr__(self) -> str:
        return f"ArabicG2P(language={self.language!r}, model={self.model_profile!r})"
