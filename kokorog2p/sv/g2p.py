"""Public Swedish G2P integration for kokorog2p."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from typing import Any

from kokorog2p.base import G2PBase
from kokorog2p.lexicons.lexphon_backend import LexphonBackend
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions, tokenize_with_offsets

from .rules import SwedishRuleEngine, SwedishRuleResult, to_kokoro


def normalize_nst_ipa_for_kokoro(ipa: str) -> str:
    """Remove NST phone separators before validating Kokoro IPA inventory."""
    return "".join(unicodedata.normalize("NFC", ipa).split(" "))


class SwedishG2P(G2PBase):
    """Native deterministic Swedish grapheme-to-phoneme converter."""

    aliases = frozenset(("sv", "sv-se", "swe", "swedish"))

    def __init__(
        self,
        language: str = "sv-se",
        *,
        use_espeak_fallback: bool = False,
        use_goruut_fallback: bool = False,
        strict: bool = False,
        version: str = "1.0",
        dialect: str = "standard",
        preserve_stress: bool = True,
        use_cli: bool = False,
        lexicons: Sequence[str] | None = None,
        store: object | None = None,
        **kwargs: Any,
    ) -> None:
        if kwargs:
            names = ", ".join(sorted(kwargs))
            raise TypeError(f"Unsupported SwedishG2P options: {names}")
        normalized_language = language.lower().replace("_", "-")
        if normalized_language not in self.aliases:
            raise ValueError(f"Unsupported Swedish language code: {language!r}")
        if version != "1.0":
            raise ValueError(f"Unsupported Swedish model version: {version!r}")
        if dialect != "standard":
            raise ValueError(f"Unsupported Swedish dialect: {dialect!r}")
        super().__init__(
            language="sv-se",
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            strict=strict,
        )
        self.version = version
        self.dialect = dialect
        self.preserve_stress = preserve_stress
        self.lexicons = () if lexicons is None else tuple(lexicons)
        self._rules = SwedishRuleEngine()
        self._lexphon = (
            LexphonBackend("sv-se", self.lexicons, store=store)
            if self.lexicons
            else None
        )

    def phonemize_word_raw(
        self, word: str, *, trace: bool = False
    ) -> SwedishRuleResult:
        return self._rules.phonemize_word_raw(word, trace=trace)

    def _render_kokoro(self, ipa: str) -> str | None:
        try:
            rendered = to_kokoro(ipa, model=self.version)
        except ValueError:
            return None
        if not self.preserve_stress:
            rendered = rendered.replace("ˈ", "").replace("ˌ", "")
        return rendered or None

    def _word_to_phonemes(self, word: str) -> str | None:
        if self._lexphon is not None:
            token = self._lexphon.lookup(word)
            if token is not None and token.known and token.pronunciation:
                rendered = self._render_kokoro(
                    normalize_nst_ipa_for_kokoro(token.pronunciation)
                )
                if rendered is not None:
                    return rendered

        result = self.phonemize_word_raw(word)
        if result.unknown_characters:
            return self._fallback_or_unknown(word)
        rendered = self._render_kokoro(result.ipa)
        if rendered is not None:
            return rendered
        return self._fallback_or_unknown(word)

    def _fallback_or_unknown(self, word: str) -> str | None:
        if self.use_espeak_fallback:
            from kokorog2p.espeak_g2p import EspeakOnlyG2P

            return EspeakOnlyG2P(
                language="sv", strict=self.strict, use_cli=self.use_cli
            ).lookup(word)
        if self.use_goruut_fallback:
            from kokorog2p.goruut_g2p import GoruutOnlyG2P

            return GoruutOnlyG2P(language="sv", strict=self.strict).lookup(word)
        if self.strict:
            raise ValueError(f"Swedish rule engine cannot phonemize {word!r}")
        return None

    def __call__(self, text: str) -> list[GToken]:
        if not text or not text.strip():
            return []
        spans = tokenize_with_offsets(text, lang="sv-se", keep_punct=True)
        tokens: list[GToken] = []
        for index, span in enumerate(spans):
            next_start = (
                spans[index + 1].char_start if index + 1 < len(spans) else len(text)
            )
            whitespace = text[span.char_end : next_start]
            if not span.text or not any(char.isalnum() for char in span.text):
                punctuation = normalize_punctuation(span.text)
                token = GToken(
                    text=span.text,
                    tag="PUNCT",
                    whitespace=whitespace,
                    phonemes=punctuation or None,
                    rating="4",
                )
            else:
                phonemes = self._word_to_phonemes(span.text)
                token = GToken(
                    text=span.text,
                    tag="X",
                    whitespace=whitespace,
                    phonemes=phonemes,
                    rating="3" if phonemes else "0",
                )
                raw = self.phonemize_word_raw(span.text, trace=True)
                token.set("raw_ipa", raw.ipa)
                token.set("rule_ids", raw.rule_ids)
                token.set("feature_tags", raw.feature_tags)
            token.set("char_start", span.char_start)
            token.set("char_end", span.char_end)
            tokens.append(token)
        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Return the selected lexicon or rule-derived Kokoro pronunciation."""
        del tag
        return self._word_to_phonemes(word)

    def get_target_model(self) -> str:
        return self.version

    def capabilities(self) -> dict[str, object]:
        return {
            "language": "sv-se",
            "native": True,
            "dialect": self.dialect,
            "version": self.version,
            "rule_based": True,
            "runtime_lexicon": bool(self.lexicons),
        }

    def close(self) -> None:
        if self._lexphon is not None:
            self._lexphon.close()

    def __repr__(self) -> str:
        return f"SwedishG2P(language={self.language!r}, version={self.version!r})"
