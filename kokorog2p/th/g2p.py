"""Lexphon-backed native Thai G2P frontend for the Wayu Kokoro model."""

from __future__ import annotations

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from lexphon import PronunciationToken

from kokorog2p.base import G2PBase
from kokorog2p.lexicons.lexphon_backend import LexphonBackend
from kokorog2p.punctuation import normalize_punctuation
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions

from .model_profile import TARGET_MODEL, adapt_lexhint_ipa, validate_output
from .normalizer import ThaiNormalizer

LatinFallback = Literal["english", "none"]


class ThaiG2PError(RuntimeError):
    """Raised when Thai pronunciation cannot be provided or represented."""


@dataclass(frozen=True)
class ThaiAnalysis:
    source: str
    normalized: str
    phonemes: str
    classification: str = "THAI"
    fallback: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Segment:
    start: int
    end: int
    token: PronunciationToken | None


class ThaiG2P(G2PBase):
    """Thai frontend using dictionary-driven ``th:lexhint`` segmentation."""

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
        lexicons: Sequence[str] | None = None,
        store: object | None = None,
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
        self.version = version
        self.latin_fallback = latin_fallback
        self._normalizer = ThaiNormalizer()
        self.lexicons = ("lexhint",) if lexicons is None else tuple(lexicons)
        self.store = store
        self._lexphon = (
            LexphonBackend("th-th", self.lexicons, store=store)
            if self.lexicons
            else None
        )
        self._english_g2p: G2PBase | None = None
        self.warnings: list[str] = []

    def get_target_model(self) -> str:
        return TARGET_MODEL

    @property
    def english_g2p(self) -> G2PBase | None:
        """Create the packaged English fallback only when a Latin run needs it."""
        if self.latin_fallback == "none":
            return None
        if self._english_g2p is None:
            from kokorog2p.en import EnglishG2P

            self._english_g2p = EnglishG2P(
                language="en-us",
                use_espeak_fallback=False,
                use_goruut_fallback=False,
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

    def _prefixes(self, text: str, position: int) -> tuple[PronunciationToken, ...]:
        if self._lexphon is None:
            return ()
        return self._lexphon.lookup_prefixes(text, position=position)

    def _segment(self, source: str) -> list[_Segment]:
        """Select the best complete segmentation using dictionary prefixes."""
        n = len(source)
        paths: list[
            tuple[int, int, int, tuple[int, ...], tuple[_Segment, ...]] | None
        ] = [None] * (n + 1)
        paths[n] = (0, 0, 0, (), ())
        for position in range(n - 1, -1, -1):
            choices: list[
                tuple[int, int, int, tuple[int, ...], tuple[_Segment, ...]]
            ] = []
            for token in self._prefixes(source, position):
                end = position + len(token.text)
                if end > n or paths[end] is None:
                    continue
                covered, unknown, segments, tie, tail = paths[end]
                choices.append(
                    (
                        covered + end - position,
                        unknown,
                        segments + 1,
                        (-(end - position), *tie),
                        (_Segment(position, end, token), *tail),
                    )
                )
            tail = paths[position + 1]
            assert tail is not None
            covered, unknown, segments, tie, rest = tail
            choices.append(
                (
                    covered,
                    unknown + 1,
                    segments + 1,
                    (0, *tie),
                    (_Segment(position, position + 1, None), *rest),
                )
            )
            paths[position] = min(
                choices, key=lambda item: (-item[0], item[1], item[2], item[3])
            )
        assert paths[0] is not None
        segments = list(paths[0][4])
        merged: list[_Segment] = []
        for segment in segments:
            if merged and segment.token is None and merged[-1].token is None:
                previous = merged[-1]
                merged[-1] = _Segment(previous.start, segment.end, None)
            else:
                merged.append(segment)
        return merged

    def _thai_tokens(self, source: str, start: int) -> list[GToken]:
        normalized = (
            source
            if getattr(self, "_kokorog2p_prepared_input", False)
            else self._normalizer.normalize(source)
        )
        tokens: list[GToken] = []
        for segment in self._segment(normalized):
            surface = normalized[segment.start : segment.end]
            phonemes: str | None = None
            if segment.token is None:
                message = f"Thai source run {source!r} has unresolved span {surface!r}."
                if self.strict:
                    raise ThaiG2PError(message)
                self.warnings.append(message)
            else:
                raw = segment.token.pronunciation
                assert raw is not None
                phonemes = adapt_lexhint_ipa(raw)
                valid, invalid = validate_output(phonemes)
                if not valid:
                    symbols = "".join(sorted(set(invalid)))
                    message = (
                        f"Thai LexHint IPA for {surface!r} contains "
                        f"unsupported symbols: {symbols}"
                    )
                    if self.strict:
                        raise ThaiG2PError(message)
                    self.warnings.append(message)
                    phonemes = None
            token = GToken(
                surface,
                tag="TH",
                phonemes=phonemes,
                rating="5" if phonemes else None,
            )
            token.set("classification", "THAI")
            token.set("normalized_source", surface)
            token.set("source", "lexicon")
            token.set("lexicon_id", "th:lexhint")
            if segment.token is not None:
                token.set("matched_key", segment.token.matched_key)
                token.set("variants", segment.token.variants)
            token.set("char_start", start + segment.start)
            token.set("char_end", start + segment.end)
            tokens.append(token)
        return tokens

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
            next_start = len(text)
            for next_source, next_run_start, _next_run_end, next_classification in runs[
                index + 1 :
            ]:
                del next_source
                if next_classification == "WHITESPACE":
                    continue
                next_start = next_run_start
                break
            whitespace = text[end:next_start]
            if classification == "THAI":
                tokens.extend(self._thai_tokens(source, start))
                if tokens:
                    tokens[-1].whitespace = whitespace
            elif classification == "LATIN":
                phonemes, fallback, warnings = self._latin_phonemes(source)
                token = GToken(
                    source, tag="LATIN", whitespace=whitespace, phonemes=phonemes
                )
                token.set("classification", "LATIN")
                token.set("fallback", fallback)
                self.warnings.extend(warnings)
                tokens.append(token)
            else:
                token = GToken(
                    source,
                    tag="PUNCT",
                    whitespace=whitespace,
                    phonemes=normalize_punctuation(source) or None,
                    rating="4",
                )
                token.set("classification", "PUNCTUATION")
                tokens.append(token)
            if classification == "THAI" and len(tokens) > 1:
                for token in tokens[:-1]:
                    if token.get("char_end") == start:
                        token.whitespace = ""
        ensure_gtoken_positions(tokens, text)
        return tokens

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        del tag
        if not word or not all(self._is_thai(char) for char in word):
            return None
        values = self._thai_tokens(word, 0)
        return " ".join(token.phonemes for token in values if token.phonemes) or None

    def capabilities(self) -> dict[str, object]:
        return {
            "language": "th-th",
            "native": True,
            "model": TARGET_MODEL,
            "tones": 5,
            "dictionary_segmentation": True,
            "lexphon": True,
            "bilingual_latin": self.latin_fallback == "english",
            "primary_engine": "lexphon",
            "latin_fallback": self.latin_fallback,
        }

    def close(self) -> None:
        if self._lexphon is not None:
            self._lexphon.close()
        if self._english_g2p is not None:
            self._english_g2p.close()

    def __repr__(self) -> str:
        return f"ThaiG2P(language={self.language!r}, model={TARGET_MODEL!r})"


__all__ = ["LatinFallback", "ThaiAnalysis", "ThaiG2P", "ThaiG2PError"]
