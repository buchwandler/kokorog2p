"""Native Northern Vietnamese G2P integrated with KokoroG2P."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

from kokorog2p.base import G2PBase
from kokorog2p.espeak_g2p import EspeakOnlyG2P
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

from .model_profile import PROFILE_NAME, TARGET_MODEL, validate_output
from .phonology import syllable_to_phones
from .render import render_syllable
from .syllable import (
    InvalidVietnameseSyllable,
    VietnameseG2PError,
    VietnameseSyllable,
    try_parse_syllable,
)
from .unicode import normalize_vietnamese

ForeignFallback = Literal["english", "espeak", "none"]


@dataclass(frozen=True)
class VietnameseAnalysis:
    """Inspectable result for one Vietnamese frontend token."""

    source: str
    normalized: str
    classification: str
    syllable: VietnameseSyllable | None
    phones: tuple[str, ...]
    rendered: str
    fallback: str | None = None


_WORD_RE = re.compile(r"(?:[\w\u0300-\u036f]+|[^\w\s\u0300-\u036f]+|\s+)", re.UNICODE)


@lru_cache(maxsize=4096)
def _cached_syllable(text: str) -> VietnameseSyllable | None:
    return try_parse_syllable(text)


@lru_cache(maxsize=4096)
def _cached_render(syllable: VietnameseSyllable) -> str:
    return render_syllable(syllable)


class VietnameseG2P(G2PBase):
    """Rule-based broad Northern/Hanoi Vietnamese frontend.

    Vietnamese orthography separates syllables with spaces. Each legal
    syllable is parsed structurally and rendered with named-tone prosody. A
    non-Vietnamese token is delegated to the configured lazy foreign backend.
    """

    profile = PROFILE_NAME
    aliases = frozenset(("vi", "vi-vn", "vie", "vietnamese"))

    def __init__(
        self,
        language: str = "vi-vn",
        *,
        version: str = TARGET_MODEL,
        foreign_fallback: ForeignFallback = "english",
        strict: bool = False,
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_cli: bool = False,
        **kwargs: Any,
    ) -> None:
        if kwargs:
            names = ", ".join(sorted(kwargs))
            raise TypeError(f"Unsupported VietnameseG2P options: {names}")
        if version not in ("1.0", "1.1"):
            raise ValueError(f"Unsupported Vietnamese model version: {version!r}")
        normalized_language = language.lower().replace("_", "-")
        if normalized_language not in self.aliases:
            raise ValueError(f"Unsupported Vietnamese language code: {language!r}")
        if foreign_fallback not in ("english", "espeak", "none"):
            raise ValueError(
                "foreign_fallback must be 'english', 'espeak', or 'none', "
                f"got {foreign_fallback!r}"
            )
        if (
            use_espeak_fallback
            and use_goruut_fallback
            and foreign_fallback == "english"
        ):
            raise ValueError("English fallback cannot enable both espeak and goruut")

        super().__init__(
            language="vi-vn",
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            strict=strict,
        )
        self.version = version
        self.foreign_fallback = foreign_fallback
        self.use_espeak_fallback = use_espeak_fallback
        self.use_goruut_fallback = use_goruut_fallback
        self.use_cli = use_cli
        self._foreign_g2p: G2PBase | None = None

    def get_target_model(self) -> str:
        """Return the model profile used for output validation."""
        return self.version

    @property
    def foreign_g2p(self) -> G2PBase | None:
        """Lazily create the configured foreign-token frontend."""
        if self.foreign_fallback == "none":
            return None
        if self._foreign_g2p is None:
            if self.foreign_fallback == "espeak":
                self._foreign_g2p = EspeakOnlyG2P(
                    language="en-us", strict=self.strict, use_cli=self.use_cli
                )
            else:
                # Import the concrete class instead of the public factory. This
                # avoids rebuilding the factory while processing a foreign word.
                from kokorog2p.en import EnglishG2P

                self._foreign_g2p = EnglishG2P(
                    language="en-us",
                    use_espeak_fallback=self.use_espeak_fallback,
                    use_goruut_fallback=self.use_goruut_fallback,
                    use_cli=self.use_cli,
                    use_spacy=False,
                    load_silver=False,
                    load_gold=True,
                    strict=self.strict,
                )
        return self._foreign_g2p

    def _foreign_word(self, word: str) -> str | None:
        backend = self.foreign_g2p
        if backend is None:
            return None
        try:
            return backend.lookup(word)
        except Exception as exc:
            if self.strict:
                raise VietnameseG2PError(
                    f"foreign fallback failed for Vietnamese token {word!r}: {exc}"
                ) from exc
            return None

    def analyze(self, text: str) -> VietnameseAnalysis:
        """Analyze one token without changing the caller's source text."""
        normalized = normalize_vietnamese(text)
        syllable = _cached_syllable(normalized)
        if syllable is not None:
            phones = syllable_to_phones(syllable)
            rendered = _cached_render(syllable)
            valid, invalid = validate_output(rendered, model=self.version)
            if not valid:
                raise VietnameseG2PError(
                    f"Vietnamese output is not valid for Kokoro {self.version}: "
                    + "".join(invalid)
                )
            return VietnameseAnalysis(
                source=text,
                normalized=normalized,
                classification="VI_SYLLABLE",
                syllable=syllable,
                phones=phones,
                rendered=rendered,
            )

        foreign = self._foreign_word(normalized)
        if foreign:
            return VietnameseAnalysis(
                source=text,
                normalized=normalized,
                classification="FOREIGN_WORD",
                syllable=None,
                phones=tuple(foreign),
                rendered=foreign,
                fallback=self.foreign_fallback,
            )
        if self.strict:
            raise InvalidVietnameseSyllable(
                "cannot parse Vietnamese token and no foreign pronunciation exists: "
                f"{text!r}"
            )
        return VietnameseAnalysis(
            source=text,
            normalized=normalized,
            classification="UNKNOWN",
            syllable=None,
            phones=(),
            rendered="",
            fallback=self.foreign_fallback,
        )

    @staticmethod
    def _is_punctuation(text: str) -> bool:
        return bool(text) and not any(char.isalnum() for char in text)

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to offset-aware :class:`GToken` objects."""
        if not text or not text.strip():
            return []

        matches = [
            match for match in _WORD_RE.finditer(text) if not match.group().isspace()
        ]
        tokens: list[GToken] = []
        for index, match in enumerate(matches):
            part = match.group()
            next_start = (
                matches[index + 1].start() if index + 1 < len(matches) else len(text)
            )
            whitespace = text[match.end() : next_start]
            if self._is_punctuation(part):
                punctuation = normalize_punctuation(part)
                token = GToken(
                    text=part,
                    tag="PUNCT",
                    whitespace=whitespace,
                    phonemes=punctuation if punctuation else None,
                )
                token.rating = "4"
            else:
                analysis = self.analyze(part)
                token = GToken(
                    text=part,
                    tag="X",
                    whitespace=whitespace,
                    phonemes=analysis.rendered or None,
                )
                token.rating = "4" if analysis.syllable is not None else "1"
                token.set("classification", analysis.classification)
                token.set("fallback", analysis.fallback)
                if analysis.syllable is not None:
                    token.set("tone", analysis.syllable.tone.value)
                    token.set("syllable", analysis.syllable)
            token.set("char_start", match.start())
            token.set("char_end", match.end())
            tokens.append(token)

        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a legal Vietnamese syllable or configured foreign word."""
        analysis = self.analyze(word)
        return analysis.rendered or None

    def phonemize(self, text: str) -> str:
        """Return the model-ready phoneme string for *text*."""
        return super().phonemize(text)

    def capabilities(self) -> dict[str, object]:
        """Return stable metadata for clients inspecting this frontend."""
        return {
            "language": "vi-vn",
            "profile": self.profile,
            "dialect": "Northern/Hanoi",
            "tones": 6,
            "native": True,
            "foreign_fallback": self.foreign_fallback,
            "model": self.version,
        }

    def __repr__(self) -> str:
        return (
            f"VietnameseG2P(language={self.language!r}, version={self.version!r}, "
            f"foreign_fallback={self.foreign_fallback!r})"
        )


__all__ = ["ForeignFallback", "VietnameseAnalysis", "VietnameseG2P"]
