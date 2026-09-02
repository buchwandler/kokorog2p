"""Native Thai G2P frontend for the Wayu Kokoro model."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import Literal

from kokorog2p.base import G2PBase
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

from .engine import EngineResult, ThaiEngine, ThaiG2PError
from .model_profile import TARGET_MODEL, validate_output
from .normalizer import ThaiNormalizer

LatinFallback = Literal["english", "none"]


@dataclass(frozen=True)
class ThaiAnalysis:
    """Inspectable result for one Thai source run."""

    source: str
    normalized: str
    phonemes: str
    classification: str = "THAI"
    fallback: str | None = None
    warnings: tuple[str, ...] = ()


class ThaiG2P(G2PBase):
    """Thai TLTK frontend with English pronunciation for Latin runs."""

    aliases = frozenset(("th", "th-th", "tha", "thai"))

    def __init__(
        self,
        language: str = "th-th",
        *,
        latin_fallback: LatinFallback = "english",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_cli: bool = False,
        strict: bool = True,
        version: str = "1.0",
        engine: ThaiEngine | None = None,
    ) -> None:
        normalized = language.lower().replace("_", "-")
        if normalized not in self.aliases:
            raise ValueError(f"Unsupported Thai language code: {language!r}")
        if latin_fallback not in ("english", "none"):
            raise ValueError("latin_fallback must be 'english' or 'none'")
        if version != "1.0":
            raise ValueError("ThaiG2P supports frontend version '1.0'.")
        super().__init__(
            language="th-th",
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
            use_cli=use_cli,
            strict=strict,
        )
        self.version = "1.0"
        self.latin_fallback = latin_fallback
        self._normalizer = ThaiNormalizer()
        self._engine = engine or ThaiEngine(strict=strict)
        self._english_g2p: G2PBase | None = None
        self.warnings: list[str] = []

    def get_target_model(self) -> str:
        """Return the model profile required for Thai token IDs."""
        return TARGET_MODEL

    @property
    def english_g2p(self) -> G2PBase | None:
        """Create the English frontend only when a Latin run needs it."""
        if self.latin_fallback == "none":
            return None
        if self._english_g2p is None:
            from kokorog2p.en import EnglishG2P

            self._english_g2p = EnglishG2P(
                language="en-us",
                use_espeak_fallback=self.use_espeak_fallback,
                use_goruut_fallback=self.use_goruut_fallback,
                use_cli=self.use_cli,
                use_spacy=False,
                load_silver=False,
                load_gold=True,
                strict=self.strict,
            )
        return self._english_g2p

    @staticmethod
    def _is_thai(char: str) -> bool:
        return "\u0e00" <= char <= "\u0e7f" or unicodedata.combining(char) != 0

    @staticmethod
    def _is_latin(char: str) -> bool:
        return char.isascii() and char.isalpha()

    @classmethod
    def _runs(cls, text: str) -> list[tuple[str, int, int, str]]:
        runs: list[tuple[str, int, int, str]] = []
        index = 0
        while index < len(text):
            start = index
            if text[index].isspace():
                index += 1
                while index < len(text) and text[index].isspace():
                    index += 1
                runs.append((text[start:index], start, index, "WHITESPACE"))
                continue
            if cls._is_thai(text[index]):
                index += 1
                while index < len(text) and cls._is_thai(text[index]):
                    index += 1
                runs.append((text[start:index], start, index, "THAI"))
                continue
            if cls._is_latin(text[index]):
                index += 1
                while index < len(text) and (
                    cls._is_latin(text[index]) or text[index] in "'’-"
                ):
                    index += 1
                # Keep a contiguous phrase together for contextual English G2P.
                while index < len(text) and text[index].isspace():
                    gap_end = index
                    while gap_end < len(text) and text[gap_end].isspace():
                        gap_end += 1
                    if gap_end >= len(text) or not cls._is_latin(text[gap_end]):
                        break
                    index = gap_end + 1
                    while index < len(text) and (
                        cls._is_latin(text[index]) or text[index] in "'’-"
                    ):
                        index += 1
                runs.append((text[start:index], start, index, "LATIN"))
                continue
            index += 1
            while (
                index < len(text)
                and not text[index].isspace()
                and not (cls._is_thai(text[index]) or cls._is_latin(text[index]))
            ):
                index += 1
            runs.append((text[start:index], start, index, "PUNCTUATION"))
        return runs

    def _thai_analysis(self, source: str) -> ThaiAnalysis:
        # Spokenform owns semantic preparation for prepared input.  Keep the
        # legacy normalizer on the raw convenience path only.
        normalized = (
            source
            if getattr(self, "_kokorog2p_prepared_input", False)
            else self._normalizer.normalize(source)
        )
        result: EngineResult = self._engine.pronounce_thai_chunk(normalized)
        phonemes = result.phonemes
        valid, invalid = validate_output(phonemes)
        warnings = list(result.warnings)
        if not valid:
            symbols = "".join(sorted(set(invalid)))
            warnings.append(f"TH_INVALID_MODEL_SYMBOL: {symbols}")
            if self.strict:
                raise ThaiG2PError(
                    f"Thai output for {source!r} contains unsupported symbols: "
                    f"{symbols}"
                )
            phonemes = "".join(char for char in phonemes if char not in invalid)
        if result.unrecovered and self.strict:
            raise ThaiG2PError(
                "Thai pronunciation could not recover lexical source units: "
                f"{result.unrecovered!r}"
            )
        return ThaiAnalysis(
            source=source,
            normalized=normalized,
            phonemes=phonemes,
            warnings=tuple(warnings),
        )

    def _latin_phonemes(self, source: str) -> tuple[str | None, str | None, list[str]]:
        backend = self.english_g2p
        if backend is None:
            return None, None, [f"TH_LATIN_UNRECOVERED: {source!r}"]
        try:
            phonemes = backend.phonemize(source)
        except Exception as exc:
            if self.strict:
                raise ThaiG2PError(
                    f"English fallback failed for Thai Latin run {source!r}: {exc}"
                ) from exc
            return None, "english", [f"TH_LATIN_UNRECOVERED: {source!r}: {exc}"]
        return phonemes or None, "english", []

    def __call__(self, text: str) -> list[GToken]:
        self.warnings = []
        if not text:
            return []
        runs = self._runs(text)
        tokens: list[GToken] = []
        for index, (source, start, end, classification) in enumerate(runs):
            if classification == "WHITESPACE":
                continue
            next_start = len(text)
            for (
                _next_source,
                next_run_start,
                _next_run_end,
                next_classification,
            ) in runs[index + 1 :]:
                if next_classification == "WHITESPACE":
                    continue
                next_start = next_run_start
                break
            whitespace = text[end:next_start]
            if classification == "THAI":
                analysis = self._thai_analysis(source)
                token = GToken(
                    source,
                    tag="TH",
                    whitespace=whitespace,
                    phonemes=analysis.phonemes or None,
                )
                token.set("classification", "THAI")
                token.set("normalized_source", analysis.normalized)
                token.set("engine", "tltk")
                token.set("fallback", None)
                self.warnings.extend(analysis.warnings)
            elif classification == "LATIN":
                phonemes, fallback, warnings = self._latin_phonemes(source)
                token = GToken(
                    source, tag="LATIN", whitespace=whitespace, phonemes=phonemes
                )
                token.set("classification", "LATIN")
                token.set("fallback", fallback)
                self.warnings.extend(warnings)
            else:
                punctuation = normalize_punctuation(source)
                token = GToken(
                    source,
                    tag="PUNCT",
                    whitespace=whitespace,
                    phonemes=punctuation or None,
                    rating="4",
                )
                token.set("classification", "PUNCTUATION")
            token.set("char_start", start)
            token.set("char_end", end)
            tokens.append(token)
        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        del tag
        if not word or not all(self._is_thai(char) for char in word):
            return None
        return self._thai_analysis(word).phonemes or None

    def capabilities(self) -> dict[str, object]:
        return {
            "language": "th-th",
            "native": True,
            "model": TARGET_MODEL,
            "tones": 5,
            "bilingual_latin": self.latin_fallback == "english",
            "primary_engine": "tltk",
            "latin_fallback": self.latin_fallback,
        }

    def __repr__(self) -> str:
        return f"ThaiG2P(language={self.language!r}, model={TARGET_MODEL!r})"


__all__ = ["LatinFallback", "ThaiAnalysis", "ThaiG2P", "ThaiG2PError"]
