"""Readable, deterministic Swedish grapheme-to-phoneme rules."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, field

from .phonology import (
    ACCEPTED_LETTERS,
    FEATURE_SUFFIXES,
    KOKORO_SUPPORTED_PHONES,
    LONG_VOWELS,
    LONGEST_GRAPHEMES,
    RETROFLEX_MAP,
    SHORT_VOWELS,
    SOFT_VOWELS,
    STRESS_NEUTRAL_SUFFIXES,
    SWEDISH_KOKORO_REMAP,
    VOWELS,
)


@dataclass
class RuleTrace:
    """Optional list of stable rule identifiers fired by one word."""

    fired: list[str] = field(default_factory=list)

    def add(self, rule_id: str) -> None:
        if rule_id not in self.fired:
            self.fired.append(rule_id)


@dataclass(frozen=True)
class Syllable:
    """Small internal syllable representation used by quantity and stress rules."""

    onset: tuple[str, ...]
    nucleus: str
    coda: tuple[str, ...]
    start: int
    end: int
    stressed: bool = False
    secondary_stress: bool = False


@dataclass(frozen=True)
class SwedishRuleResult:
    word: str
    phones: tuple[str, ...]
    stress_syllable: int | None = None
    rule_ids: tuple[str, ...] = ()
    feature_tags: tuple[str, ...] = ()
    unknown_characters: tuple[str, ...] = ()

    @property
    def ipa(self) -> str:
        return "".join(self.phones)


@dataclass(frozen=True)
class _Segment:
    spelling: str
    start: int
    end: int


class SwedishRuleEngine:
    """Pure rule-based Swedish frontend producing reference-style IPA tokens."""

    version = "sv-rules-v0.1"

    def phonemize_word_raw(
        self, word: str, *, trace: bool = False
    ) -> SwedishRuleResult:
        normalized = unicodedata.normalize("NFC", word).casefold()
        tracer = RuleTrace() if trace else None
        if normalized != word:
            _mark(tracer, "SV-N-001-NFC")
            _mark(tracer, "SV-N-002-CASEFOLD")

        unknown = tuple(
            sorted(
                {
                    char
                    for char in normalized
                    if char.isalpha() and char not in ACCEPTED_LETTERS
                }
            )
        )
        if unknown:
            _mark(tracer, "SV-N-003-UNKNOWN")

        segments = self._segment(normalized, tracer)
        features = self._features(normalized, tracer)
        stress_syllable, stressed_segment = self._assign_stress(
            normalized, segments, tracer
        )
        phones = self._convert(
            normalized,
            segments,
            stressed_segment,
            stress_syllable,
            tracer,
        )
        phones = self._apply_retroflexion(phones, tracer)
        if unknown:
            phones.extend("?")
        return SwedishRuleResult(
            word=normalized,
            phones=tuple(phones),
            stress_syllable=stress_syllable,
            rule_ids=tuple(tracer.fired) if tracer else (),
            feature_tags=tuple(features),
            unknown_characters=unknown,
        )

    def phonemize_word(self, word: str, *, trace: bool = False) -> SwedishRuleResult:
        """Alias retaining an explicit raw-result API for callers and benchmarks."""
        return self.phonemize_word_raw(word, trace=trace)

    def _segment(self, word: str, trace: RuleTrace | None) -> list[_Segment]:
        segments: list[_Segment] = []
        position = 0
        while position < len(word):
            matched = False
            for spelling, _phone, rule_id in LONGEST_GRAPHEMES:
                if word.startswith(spelling, position):
                    segments.append(
                        _Segment(spelling, position, position + len(spelling))
                    )
                    _mark(trace, rule_id)
                    position += len(spelling)
                    matched = True
                    break
            if not matched:
                segments.append(_Segment(word[position], position, position + 1))
                position += 1
        return segments

    def _features(self, word: str, trace: RuleTrace | None) -> list[str]:
        features: list[str] = []
        for spelling, tag in FEATURE_SUFFIXES:
            if word.endswith(spelling):
                features.append(tag)
                _mark(trace, f"SV-S-FEATURE-{tag.upper()}")
        if "c" in word:
            features.append("contains_c")
        if "x" in word:
            features.append("contains_x")
        if "w" in word:
            features.append("contains_w")
        if any(word[index] == word[index + 1] for index in range(len(word) - 1)):
            features.append("double_consonant")
        if len(word) >= 12:
            features.append("word_length_9_plus")
        for first, second, tag in (
            ("sk", "", "contains_sk"),
            ("sj", "", "contains_sj"),
            ("skj", "", "contains_skj"),
            ("stj", "", "contains_stj"),
            ("sch", "", "contains_sch"),
            ("tj", "", "contains_tj"),
            ("kj", "", "contains_kj"),
            ("ng", "", "contains_ng"),
        ):
            if first + second in word and tag not in features:
                features.append(tag)
        for source, tag in (
            ("t", "r_before_t"),
            ("d", "r_before_d"),
            ("n", "r_before_n"),
            ("s", "r_before_s"),
            ("l", "r_before_l"),
        ):
            if f"r{source}" in word:
                features.append(tag)
        if word.endswith(("t", "d", "n", "s", "l")) and "r" in word:
            _mark(trace, "SV-P-RETROFLEX-CANDIDATE")
        for vowel in VOWELS:
            if vowel in word:
                features.append(f"contains_{vowel}")
        return features

    def _assign_stress(
        self,
        word: str,
        segments: list[_Segment],
        trace: RuleTrace | None,
    ) -> tuple[int | None, int | None]:
        vowel_segments = [
            index
            for index, segment in enumerate(segments)
            if segment.spelling in VOWELS
        ]
        if not vowel_segments:
            return None, None
        stressed_segment = vowel_segments[0]
        if "é" in word:
            stressed_segment = next(
                index for index in vowel_segments if segments[index].spelling == "é"
            )
            _mark(trace, "SV-S-001-EXPLICIT-E-ACUTE")
        elif word.endswith(("tion", "sion")):
            stressed_segment = vowel_segments[-1]
            _mark(trace, "SV-S-100-SUFFIX-STRESS")
        elif word.endswith(STRESS_NEUTRAL_SUFFIXES):
            _mark(trace, "SV-S-020-INFLECTIONAL-END")
        else:
            _mark(trace, "SV-S-010-FIRST-SYLLABLE")
        stress_syllable = vowel_segments.index(stressed_segment)
        return stress_syllable, stressed_segment

    def _convert(
        self,
        word: str,
        segments: list[_Segment],
        stressed_segment: int | None,
        stress_syllable: int | None,
        trace: RuleTrace | None,
    ) -> list[str]:
        phones: list[str] = []
        vowel_number = 0
        for index, segment in enumerate(segments):
            spelling = segment.spelling
            next_letter = word[segment.end] if segment.end < len(word) else ""
            if spelling in VOWELS:
                if index == stressed_segment:
                    phones.append("ˈ")
                long = self._is_long_vowel(
                    word, segment, index == stressed_segment, trace
                )
                phone = LONG_VOWELS[spelling] if long else SHORT_VOWELS[spelling]
                _mark(trace, f"SV-V-{'LONG' if long else 'SHORT'}-{spelling}")
                phones.append(phone)
                vowel_number += 1
                continue
            if spelling == "sk":
                if next_letter in SOFT_VOWELS:
                    phones.append("ɧ")
                    _mark(trace, "SV-C-120-SOFT-SK")
                else:
                    phones.extend(("s", "k"))
                    _mark(trace, "SV-C-121-HARD-SK")
                continue
            if spelling == "g":
                if next_letter in SOFT_VOWELS:
                    phones.append("j")
                    _mark(trace, "SV-C-100-SOFT-G")
                else:
                    phones.append("ɡ")
                    _mark(trace, "SV-C-101-HARD-G")
                continue
            if spelling == "k":
                if next_letter in SOFT_VOWELS:
                    phones.append("ɕ")
                    _mark(trace, "SV-C-110-SOFT-K")
                else:
                    phones.append("k")
                    _mark(trace, "SV-C-111-HARD-K")
                continue
            if spelling == "c":
                phones.append("s" if next_letter in SOFT_VOWELS else "k")
                _mark(
                    trace,
                    "SV-C-130-SOFT-C"
                    if next_letter in SOFT_VOWELS
                    else "SV-C-131-HARD-C",
                )
                continue
            if spelling == "x":
                phones.extend(("k", "s"))
                _mark(trace, "SV-C-140-X")
                continue
            if spelling == "w":
                phones.append("v")
                _mark(trace, "SV-C-141-W")
                continue
            if spelling == "z":
                phones.append("s")
                _mark(trace, "SV-C-142-Z")
                continue
            if spelling == "q":
                phones.append("k")
                _mark(trace, "SV-C-143-Q")
                continue
            if spelling in {"sj", "skj", "stj", "sch"}:
                phones.append("ɧ")
                continue
            if spelling in {"tj", "kj"}:
                phones.append("ɕ")
                continue
            if spelling in {"dj", "gj", "hj", "lj"}:
                phones.append("j")
                continue
            if spelling == "ng":
                phones.append("ŋ")
                continue
            if spelling in ("ck", "qu", "qv"):
                phones.extend("k" if spelling == "ck" else ("k", "v"))
                continue
            phones.append(self._simple_consonant(spelling))
        return phones

    def _is_long_vowel(
        self,
        word: str,
        segment: _Segment,
        stressed: bool,
        trace: RuleTrace | None,
    ) -> bool:
        if not stressed:
            _mark(trace, "SV-V-001-UNSTRESSED")
            return False
        following = word[segment.end :]
        if len(following) == 0:
            _mark(trace, "SV-V-030-OPEN")
            return True
        next_vowel = next(
            (index for index, char in enumerate(following) if char in VOWELS), None
        )
        consonants = following if next_vowel is None else following[:next_vowel]
        if len(consonants) >= 2 or (
            consonants and consonants[0] == consonants[1]
            if len(consonants) > 1
            else False
        ):
            _mark(trace, "SV-V-020-CLUSTER-SHORT")
            return False
        if len(consonants) == 1 and next_vowel is None:
            _mark(trace, "SV-V-040-FINAL-SINGLE-C-LONG")
            return True
        _mark(trace, "SV-V-030-OPEN")
        return True

    @staticmethod
    def _simple_consonant(spelling: str) -> str:
        from .phonology import SIMPLE_CONSONANTS

        return SIMPLE_CONSONANTS.get(spelling, spelling)

    def _apply_retroflexion(
        self, phones: list[str], trace: RuleTrace | None
    ) -> list[str]:
        result: list[str] = []
        index = 0
        while index < len(phones):
            if (
                index + 1 < len(phones)
                and (phones[index], phones[index + 1]) in RETROFLEX_MAP
            ):
                pair = (phones[index], phones[index + 1])
                result.append(RETROFLEX_MAP[pair])
                _mark(trace, f"SV-P-RETROFLEX-{pair[0].upper()}{pair[1].upper()}")
                index += 2
            else:
                result.append(phones[index])
                index += 1
        return result


def _mark(trace: RuleTrace | None, rule_id: str) -> None:
    if trace is not None:
        trace.add(rule_id)


_DEFAULT_ENGINE = SwedishRuleEngine()


def phonemize_word_raw(word: str, *, trace: bool = False) -> SwedishRuleResult:
    return _DEFAULT_ENGINE.phonemize_word_raw(word, trace=trace)


def to_kokoro(ipa: str, *, model: str = "1.0") -> str:
    """Adapt raw Swedish IPA to the explicit supported Kokoro inventory."""
    if model != "1.0":
        raise ValueError(f"Unsupported Swedish Kokoro model: {model!r}")
    result = ipa
    for source, target in sorted(
        SWEDISH_KOKORO_REMAP.items(), key=lambda item: -len(item[0])
    ):
        result = result.replace(source, target)
    result = result.replace("r", "ɹ")
    unsupported = sorted(set(result) - KOKORO_SUPPORTED_PHONES)
    if unsupported:
        symbols = "".join(unsupported)
        raise ValueError(f"Swedish IPA contains unsupported Kokoro phones: {symbols}")
    return result


__all__ = [
    "RuleTrace",
    "SwedishRuleEngine",
    "SwedishRuleResult",
    "Syllable",
    "phonemize_word_raw",
    "to_kokoro",
]
