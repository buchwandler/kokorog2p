"""German G2P (Grapheme-to-Phoneme) converter.

Grapheme to Phoneme for German language using dictionary lookup
with rule-based fallback.

German Phonology features:
- Final obstruent devoicing (Auslautverhärtung)
- Vowel length distinction
- Umlauts (ä, ö, ü)
- ß (Eszett)
- CH as [ç] or [x] depending on context (ich-Laut vs ach-Laut)
- Voicing assimilation in consonant clusters
- Schwa in unstressed syllables

Reference:
https://en.wikipedia.org/wiki/Standard_German_phonology
"""

from __future__ import annotations

import time
import unicodedata
from collections import defaultdict
from collections.abc import Collection, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Final

from kokorog2p._optional import load_spacy_model
from kokorog2p.base import G2PBase
from kokorog2p.pipeline.tokenizer import RegexTokenizer, SpacyTokenizer
from kokorog2p.spacy_models import resolve_spacy_model
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions
from kokorog2p.vocab import get_vocab

if TYPE_CHECKING:
    from lexphon import DataStore

    from kokorog2p.de.lexicon import GermanLexicon
# =============================================================================
# German Phoneme Mappings
# =============================================================================

# Basic IPA mappings for German graphemes
# Note: Many mappings are context-dependent and handled by rules
IPA: Final[dict[str, str]] = {
    # Vowels - short
    "a": "a",
    "e": "ɛ",
    "i": "ɪ",
    "o": "ɔ",
    "u": "ʊ",
    "ä": "ɛ",
    "ö": "œ",
    "ü": "ʏ",
    "y": "ʏ",
    # Vowels - long (marked with doubling or followed by h/single consonant)
    "aa": "aː",
    "ee": "eː",
    "ie": "iː",
    "oo": "oː",
    "uh": "uː",
    "äh": "ɛː",
    "öh": "øː",
    "üh": "yː",
    "ah": "aː",
    "eh": "eː",
    "ih": "iː",
    "oh": "oː",
    # Diphthongs
    "ei": "aɪ",
    "ai": "aɪ",
    "ey": "aɪ",
    "ay": "aɪ",
    "au": "aʊ",
    "eu": "ɔʏ",
    "äu": "ɔʏ",
    # Consonants
    "b": "b",
    "c": "k",
    "d": "d",
    "f": "f",
    "g": "ɡ",
    "h": "h",
    "j": "j",
    "k": "k",
    "l": "l",
    "m": "m",
    "n": "n",
    "p": "p",
    "q": "k",
    "r": "ʁ",
    "s": "z",  # Default voiced, devoiced in certain contexts
    "t": "t",
    "v": "f",  # Usually [f] in German
    "w": "v",
    "x": "ks",
    "z": "ʦ",
    "ß": "s",
    # Digraphs and trigraphs
    "ch": "x",  # Default ach-Laut, ich-Laut handled by rule
    "ck": "k",
    "dt": "t",
    "ng": "ŋ",
    "nk": "ŋk",
    "ph": "f",
    "pf": "pf",
    "qu": "kv",
    "sch": "ʃ",
    "sp": "ʃp",  # Word-initial
    "st": "ʃt",  # Word-initial
    "ss": "s",
    "th": "t",
    "tz": "ʦ",
    "tsch": "ʧ",
    "dsch": "ʤ",
    "chs": "ks",
}

# Voiced-unvoiced consonant pairs for final devoicing
VOICED_TO_UNVOICED: Final[dict[str, str]] = {
    "b": "p",
    "d": "t",
    "g": "k",
    "ɡ": "k",  # IPA g (U+0261)
    "v": "f",
    "z": "s",
    "ʒ": "ʃ",
}


def _is_front_vowel_context(prev_chars: str) -> bool:
    """Check if the previous character(s) form a front vowel context for ich-Laut."""
    prev_lower = prev_chars.lower()
    # Check for front vowels and consonants l, n, r
    if prev_lower in ("i", "e", "ä", "ö", "ü", "y"):
        return True
    if prev_lower in ("l", "n", "r"):
        return True
    # Check for diphthongs ending in front vowel
    return bool(prev_lower.endswith(("ei", "ai", "eu", "äu", "ie", "ey", "ay")))


@dataclass(frozen=True, slots=True)
class GermanPhonemeNormalization:
    """Classified result of converting German/Crane IPA for a model."""

    value: str
    valid: bool
    replacements: tuple[tuple[str, str], ...]
    ignored: tuple[str, ...]
    unsupported: tuple[str, ...]


_IGNORED_SOURCE_MARKS: Final[frozenset[str]] = frozenset(
    {
        "̯",  # Non-syllabic mark: the Kokoro consumer encodes the diphthong itself.
        "̩",  # Syllabic mark: German syllabic consonants use the consonant token.
        "-",
        "[",
        "]",
        "1",
        "(",
        ")",  # Transcription delimiters/boundaries.
        "̍",
        "̑",
        "̚",
        "̝",
        "̞",
        "̢",
        "̥",
        "̪",
        "̺",  # Articulatory detail.
        "̆",
        "̈",
        "̊",
        "ˑ",
        "ˠ",
        "ˣ",
        "˥",
        "ꜜ",
        "ʶ",  # Non-model prosodic detail.
        "͜",
        "͡",
        "‿",  # Joining marks after known affricates are resolved.
    }
)
_GERMAN_CONVERSION_TABLE: Final[dict[str, str]] = {
    # Crane/benchmark affricates and diphthongs.
    "t͡s": "ʦ",
    "t͡ʃ": "ʧ",
    "d͡ʒ": "ʤ",
    "d͡z": "ʣ",
    "ts": "ʦ",
    "dz": "ʣ",
    "aɪ": "I",
    "aʊ": "W",
    "ɔʏ": "ɔy",
    # Tie-bar forms used by the German rule fallback.
    "a^ɪ": "I",
    "a^ʊ": "W",
    "d^z": "ʣ",
    "d^ʒ": "ʤ",
    "e^ɪ": "A",
    "o^ʊ": "O",
    "ə^ʊ": "Q",
    "s^s": "S",
    "t^s": "ʦ",
    "t^ʃ": "ʧ",
    "ɔ^ɪ": "Y",
    "p͡f": "pf",
    # Explicit approximations for foreign/loanword IPA in the source inventory.
    "K": "k",
    "ĕ": "e",
    "ĭ": "i",
    "ǃ": "ʔ",
    "ʕ": "ʔ",
    "ʱ": "h",
    "з": "z",
    "ɱ": "m",
    "ɫ": "l",
    "ɬ": "l",
    "ʀ": "ʁ",
    "ʉ": "u",
    "ɘ": "ə",
    "ɶ": "œ",
    "ɝ": "ɜ",
    "ʑ": "ʒ",
    "ɺ": "l",
    "ʙ": "b",
    "ɓ": "b",
    "ħ": "h",
    "õ": "o",
    "ã": "a",
    "ẽ": "e",
    "ạ": "a",
    "ọ": "o",
    "ʏ": "y",
}
_SORTED_GERMAN_CONVERSIONS: Final[tuple[tuple[str, str], ...]] = tuple(
    sorted(
        _GERMAN_CONVERSION_TABLE.items(), key=lambda item: len(item[0]), reverse=True
    )
)
_GERMAN_CONVERSIONS_BY_FIRST: Final[dict[str, tuple[tuple[str, str], ...]]] = {
    char: tuple(item for item in _SORTED_GERMAN_CONVERSIONS if item[0].startswith(char))
    for char in {item[0][0] for item in _SORTED_GERMAN_CONVERSIONS}
}


def normalize_internal(
    phonemes: str,
    *,
    vocabulary: Collection[str] | None = None,
    model: str = "1.0",
    use_tie_replacement: bool = False,
) -> GermanPhonemeNormalization:
    """Classify and normalize IPA without silently discarding source material."""
    target = get_vocab(model) if vocabulary is None else vocabulary
    source = unicodedata.normalize("NFC", phonemes)
    output: list[str] = []
    replacements: list[tuple[str, str]] = []
    ignored: list[str] = []
    unsupported: list[str] = []
    index = 0
    while index < len(source):
        matched = False
        if use_tie_replacement:
            for old, new in _GERMAN_CONVERSIONS_BY_FIRST.get(source[index], ()):
                if source.startswith(old, index):
                    output.append(new)
                    replacements.append((old, new))
                    index += len(old)
                    matched = True
                    break
        else:
            # The caret is an internal fallback marker, not a source symbol.
            for old, new in _GERMAN_CONVERSIONS_BY_FIRST.get(source[index], ()):
                if "^" in old or "͡" in old:
                    continue
                if source.startswith(old, index):
                    output.append(new)
                    replacements.append((old, new))
                    index += len(old)
                    matched = True
                    break
        if matched:
            continue
        char = source[index]
        if char in _IGNORED_SOURCE_MARKS:
            ignored.append(char)
            index += 1
            continue
        if char in target:
            output.append(char)
        else:
            # Preserve rejected material in the result so a caller cannot mistake
            # classified loss for a valid target string.
            output.append(char)
            unsupported.append(char)
        index += 1
    value = "".join(output)
    valid = bool(value) and not unsupported and all(char in target for char in value)
    return GermanPhonemeNormalization(
        value=value,
        valid=valid,
        replacements=tuple(replacements),
        ignored=tuple(ignored),
        unsupported=tuple(unsupported),
    )


def normalize_to_kokoro(
    phonemes: str,
    use_tie_replacement: bool = False,
    *,
    vocabulary: Collection[str] | None = None,
    model: str = "1.0",
) -> str:
    """Return strict German IPA conversion or raise for unrepresentable input."""
    result = normalize_internal(
        phonemes,
        vocabulary=vocabulary,
        model=model,
        use_tie_replacement=use_tie_replacement,
    )
    if not result.valid:
        detail = ", ".join(repr(item) for item in result.unsupported)
        raise ValueError(
            "German IPA contains unhandled or empty material"
            + (f": {detail}" if detail else "")
        )
    return result.value


@dataclass
class GermanG2PStats:
    """Opt-in aggregate diagnostics for one or more German G2P calls."""

    words: int = 0
    lexicon_calls: int = 0
    lexicon_hits: int = 0
    lexicon_misses: int = 0
    lexicon_ns: int = 0
    fallback_calls: int = 0
    fallback_hits: int = 0
    fallback_misses: int = 0
    fallback_ns: int = 0
    rule_calls: int = 0
    rules_ns: int = 0
    source_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    slow_tokens: list[dict[str, Any]] = field(default_factory=list)
    max_slow_tokens: int = 15

    def add_slow_token(self, token: str, source: str, elapsed_ns: int) -> None:
        self.slow_tokens.append(
            {"token": token, "source": source, "elapsed_ms": elapsed_ns / 1_000_000}
        )
        self.slow_tokens.sort(key=lambda item: item["elapsed_ms"], reverse=True)
        del self.slow_tokens[self.max_slow_tokens :]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


_ACTIVE_DIAGNOSTICS: ContextVar[GermanG2PStats | None] = ContextVar(
    "kokorog2p_german_diagnostics", default=None
)


@contextmanager
def capture_diagnostics(*, max_slow_tokens: int = 15) -> Iterator[GermanG2PStats]:
    """Collect German source and timing counters for the enclosed calls."""
    stats = GermanG2PStats(max_slow_tokens=max_slow_tokens)
    token = _ACTIVE_DIAGNOSTICS.set(stats)
    try:
        yield stats
    finally:
        _ACTIVE_DIAGNOSTICS.reset(token)


class GermanG2P(G2PBase):
    """German G2P converter using dictionary lookup with fallback options.

    This class provides grapheme-to-phoneme conversion for German text
    using a large dictionary (738k+ entries) with fallback to espeak-ng
    or goruut for out-of-vocabulary words and phonological rules.

    Example:
        >>> g2p = GermanG2P()
        >>> tokens = g2p("Guten Tag")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    def __init__(
        self,
        language: str = "de-de",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_spacy: bool = False,
        spacy_model: str | None = None,
        use_lexicon: bool = True,
        strip_stress: bool = True,
        load_silver: bool | None = None,
        load_gold: bool | None = None,
        lexicons: tuple[str, ...] | None = None,
        version: str = "1.0",
        store: DataStore | None = None,
    ) -> None:
        """Initialize the German G2P converter.

        Args:
            language: Language code (default: 'de-de').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            use_spacy: Whether to use spaCy for tokenization and POS tagging.
                Defaults to False to preserve legacy behavior and avoid requiring
                spaCy model downloads unless explicitly requested.
            spacy_model: spaCy German model package to load when use_spacy=True
                (e.g., "de_core_news_sm", "de_core_news_md", "de_core_news_lg").
            use_lexicon: Whether to use dictionary lookup (default: True).
            strip_stress: Whether to remove stress markers from lexicon output.
            load_silver: If True, load silver tier dictionary if available.
                Currently German only has gold dictionary, so this parameter
                is reserved for future use and consistency with English.
                Defaults to True for consistency.
            load_gold: If True, load gold tier dictionary.
                Defaults to True for maximum quality and coverage.
                Set to False when ultra-fast initialization is needed.
        Raises:
            ValueError: If both use_espeak_fallback and use_goruut_fallback are True.
        """
        # Validate mutual exclusion
        if use_espeak_fallback and use_goruut_fallback:
            raise ValueError(
                "Cannot use both espeak and goruut fallback simultaneously. "
                "Please set only one of use_espeak_fallback or "
                "use_goruut_fallback to True."
            )

        super().__init__(
            language=language,
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
        )
        self.version = version
        self._vocabulary = frozenset(get_vocab(version))
        self._lexicon: GermanLexicon | None = None
        self.lexicon: GermanLexicon | None = None
        self._fallback: Any = None
        self._strip_stress = strip_stress
        if use_spacy and (spacy_model is None or spacy_model.lower() == "auto"):
            spacy_model = resolve_spacy_model(
                language,
                spacy_model=spacy_model,
            ).package
        self.use_spacy = use_spacy
        self.spacy_model = spacy_model

        # Initialize spaCy and tokenizers (lazy)
        self._nlp: object | None = None
        self._regex_tokenizer: RegexTokenizer | None = None
        self._spacy_tokenizer: SpacyTokenizer | None = None

        # Initialize normalizer
        from kokorog2p.de.normalizer import GermanNormalizer

        self._normalizer = GermanNormalizer(
            track_changes=False,
        )

        if use_lexicon:
            from kokorog2p.de.lexicon import GermanLexicon

            self._lexicon = GermanLexicon(
                strip_stress=strip_stress,
                load_silver=load_silver,
                load_gold=load_gold,
                lexicons=lexicons,
                store=store,
            )
            self.lexicon = self._lexicon

        # Initialize fallback (lazy)
        if use_goruut_fallback:
            try:
                from kokorog2p.de.fallback import GermanGoruutFallback

                self._fallback = GermanGoruutFallback()
            except ImportError:
                pass
        elif use_espeak_fallback:
            try:
                from kokorog2p.de.fallback import GermanEspeakFallback

                self._fallback = GermanEspeakFallback()
            except ImportError:
                pass

    @property
    def nlp(self) -> object:
        """Lazily initialize spaCy."""
        if self._nlp is None:
            if self.spacy_model is None:
                raise RuntimeError(
                    "spaCy model is required when spaCy tokenization is enabled"
                )
            self._nlp = load_spacy_model(self.spacy_model, enable=["tok2vec", "tagger"])
        return self._nlp

    @property
    def regex_tokenizer(self) -> RegexTokenizer:
        """Lazily initialize the regex tokenizer."""
        if self._regex_tokenizer is None:
            self._regex_tokenizer = RegexTokenizer(
                track_positions=True,
                use_bracket_matching=True,
                lang=self.language,
            )
        return self._regex_tokenizer

    @property
    def spacy_tokenizer(self) -> SpacyTokenizer:
        """Lazily initialize the spaCy tokenizer."""
        if self._spacy_tokenizer is None:
            self._spacy_tokenizer = SpacyTokenizer(
                nlp=self.nlp,
                track_positions=True,
                use_bracket_matching=True,
                lang=self.language,
            )
        return self._spacy_tokenizer

    def _decode_lexicon_pronunciation(self, phonemes: str) -> str | None:
        """Normalize a raw lexicon pronunciation for the target vocabulary."""
        normalized = normalize_internal(
            phonemes,
            use_tie_replacement=True,
            vocabulary=self._vocabulary,
        )
        if not normalized.valid:
            return None
        return normalized.value

    def __call__(self, text: str) -> list[GToken]:  # noqa: C901
        """Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        if not text or not text.strip():
            return []

        # Prepared input already owns written-to-spoken semantics; retain only
        # the G2P typography layer in that mode.
        if getattr(self, "_kokorog2p_prepared_input", False):
            text = self._normalizer.normalize_for_g2p(text)
        else:
            text = self._normalizer(text)

        tokens = (
            self._tokenize_spacy(text)
            if self.use_spacy
            else self._tokenize_simple(text)
        )

        diagnostics = _ACTIVE_DIAGNOSTICS.get()
        fallback_tokens: list[GToken] = []
        for token in tokens:
            word = token.text
            is_word = any(c.isalnum() for c in word)
            if diagnostics is not None and is_word:
                diagnostics.words += 1

            if not is_word:
                token.phonemes = self._get_punct_phonemes(word)
                token.set("rating", 4)
                continue

            phonemes = None
            if self._lexicon is not None:
                if diagnostics is not None:
                    diagnostics.lexicon_calls += 1
                    lookup_started = time.perf_counter_ns()
                raw_phonemes = self._lexicon.lookup(word, token.tag)
                if diagnostics is not None:
                    elapsed = time.perf_counter_ns() - lookup_started
                    diagnostics.lexicon_ns += elapsed
                    diagnostics.add_slow_token(word, "lexicon", elapsed)
                phonemes = (
                    self._decode_lexicon_pronunciation(raw_phonemes)
                    if raw_phonemes
                    else None
                )
                if phonemes:
                    if diagnostics is not None:
                        diagnostics.lexicon_hits += 1
                    token.phonemes = phonemes
                    token.set("rating", 5)
                else:
                    if diagnostics is not None:
                        diagnostics.lexicon_misses += 1
                    phonemes = None

            if not phonemes and self._fallback is not None:
                fallback_tokens.append(token)
            elif not phonemes:
                token.set("rating", 0)

        if fallback_tokens and self._fallback is not None:
            fallback_words = [token.text for token in fallback_tokens]
            if diagnostics is not None:
                diagnostics.fallback_calls += len(fallback_words)
                fallback_started = time.perf_counter_ns()
            fallback_many = getattr(self._fallback, "phonemize_many", None)
            fallback_results = (
                fallback_many(fallback_words)
                if callable(fallback_many)
                else [self._fallback(word) for word in fallback_words]
            )
            if diagnostics is not None:
                elapsed = time.perf_counter_ns() - fallback_started
                diagnostics.fallback_ns += elapsed
                diagnostics.add_slow_token("<batch>", "fallback", elapsed)
            if len(fallback_results) != len(fallback_tokens):
                raise RuntimeError("Fallback returned an invalid batch length")
            for token, fallback_result in zip(
                fallback_tokens, fallback_results, strict=True
            ):
                phonemes = fallback_result[0]
                if phonemes:
                    if diagnostics is not None:
                        diagnostics.fallback_hits += 1
                    token.phonemes = phonemes
                    token.set("rating", 3)
                elif diagnostics is not None:
                    diagnostics.fallback_misses += 1
                    token.set("rating", 0)

        for token in tokens:
            if not any(c.isalnum() for c in token.text) or token.phonemes:
                continue
            word = token.text
            if diagnostics is not None:
                diagnostics.rule_calls += 1
                rules_started = time.perf_counter_ns()
            phonemes = self._word_to_phonemes(word)
            if diagnostics is not None:
                elapsed = time.perf_counter_ns() - rules_started
                diagnostics.rules_ns += elapsed
                diagnostics.add_slow_token(word, "rules", elapsed)
            if phonemes:
                normalized = normalize_internal(phonemes, vocabulary=self._vocabulary)
                if normalized.valid:
                    token.phonemes = normalized.value
                    token.set("rating", 2)
                else:
                    phonemes = None
            if not phonemes:
                token.phonemes = "?"
                token.set("rating", 0)

        if diagnostics is not None:
            for token in tokens:
                if not any(c.isalnum() for c in token.text):
                    continue
                if token.get("rating") == 0:
                    diagnostics.source_counts["unresolved"] += 1
                else:
                    source = {5: "lexicon", 3: "espeak_fallback", 2: "german_rules"}[
                        token.get("rating")
                    ]
                    diagnostics.source_counts[source] += 1

        ensure_gtoken_positions(tokens, text)
        return tokens

    def _tokenize_spacy(self, text: str) -> list[GToken]:
        """Tokenize text using spaCy."""
        processing_tokens = self.spacy_tokenizer.tokenize(text)
        return [ptoken.to_gtoken() for ptoken in processing_tokens]

    def _tokenize_simple(self, text: str) -> list[GToken]:
        """Tokenize text using regex tokenizer."""
        processing_tokens = self.regex_tokenizer.tokenize(text)
        return [ptoken.to_gtoken() for ptoken in processing_tokens]

    def _word_to_phonemes(self, word: str) -> str:
        """Convert a single word to phonemes using German rules.

        Args:
            word: Word to convert.

        Returns:
            Phoneme string in IPA.
        """
        text = word.lower()
        result: list[str] = []
        i = 0
        n = len(text)

        while i < n:
            matched = False

            # Try to match multi-character sequences first (longest match)
            for length in (4, 3, 2):
                if i + length <= n:
                    chunk = text[i : i + length]

                    # Special handling for 'ch'
                    if chunk == "ch" and length == 2:
                        # ich-Laut vs ach-Laut
                        if i == 0:
                            # Word-initial ch (loan words) -> [ç] or [k]
                            result.append("ç")
                        elif i > 0 and _is_front_vowel_context(text[i - 1]):
                            # After front vowels and l, n, r -> ich-Laut [ç]
                            result.append("ç")
                        else:
                            # After back vowels a, o, u, au -> ach-Laut [x]
                            result.append("x")
                        i += 2
                        matched = True
                        break

                    # Special handling for word-initial sp, st
                    if chunk in ("sp", "st") and length == 2:
                        if i == 0:
                            # Word-initial sp/st -> [ʃp]/[ʃt]
                            result.append("ʃ")
                            result.append(chunk[1])
                            i += 2
                            matched = True
                            break
                        # Not word-initial, handle normally
                        continue

                    # Special handling for 'ig' at word end
                    if chunk == "ig" and length == 2 and i + 2 == n:
                        result.append("ɪ")
                        result.append("ç")  # -ig -> [ɪç] at word end
                        i += 2
                        matched = True
                        break

                    # Check if chunk is in IPA mappings
                    if chunk in IPA:
                        result.append(IPA[chunk])
                        i += length
                        matched = True
                        break

            if matched:
                continue

            # Single character
            char = text[i]

            # Special handling for vowels - check for length
            if char in "aeiouäöü":
                phoneme = self._get_vowel_phoneme(text, i)
                result.append(phoneme)
                i += 1
                continue

            # Special handling for 's'
            if char == "s":
                # Word-final or before unvoiced consonant -> [s]
                if i == n - 1 or i + 1 < n and text[i + 1] in "ptk":
                    result.append("s")
                else:
                    # Before vowel -> [z]
                    result.append("z")
                i += 1
                continue

            # Special handling for 'v'
            if char == "v":
                # In some loan words, 'v' is [v], but default is [f]
                result.append("f")
                i += 1
                continue

            # Special handling for 'r'
            if char == "r":
                # Vocalized r at end of syllable/word often becomes [ɐ]
                # For simplicity, use [ʁ] everywhere
                result.append("ʁ")
                i += 1
                continue

            # Check IPA mapping
            if char in IPA:
                result.append(IPA[char])
            elif char.isalpha():
                # Unknown letter, keep as-is or use placeholder
                result.append(char)
            # Skip non-alphabetic characters

            i += 1

        # Apply final devoicing
        result = self._apply_final_devoicing(result)

        return "".join(result)

    def _get_vowel_phoneme(self, text: str, pos: int) -> str:
        """Determine the correct vowel phoneme based on context.

        German vowel length is determined by syllable structure:
        - Long in open syllables (single consonant + vowel follows)
        - Long before single consonant at word end in many cases
        - Short before consonant clusters
        - Schwa (ə) in unstressed endings like -e, -en, -el, -er

        Args:
            text: The full word text.
            pos: Position of the vowel in the word.

        Returns:
            IPA phoneme for the vowel.
        """
        char = text[pos]

        # Short vowel mappings
        short_vowels: dict[str, str] = {
            "a": "a",
            "e": "ɛ",
            "i": "ɪ",
            "o": "ɔ",
            "u": "ʊ",
            "ä": "ɛ",
            "ö": "œ",
            "ü": "ʏ",
        }

        # Long vowel mappings
        long_vowels: dict[str, str] = {
            "a": "aː",
            "e": "eː",
            "i": "iː",
            "o": "oː",
            "u": "uː",
            "ä": "ɛː",
            "ö": "øː",
            "ü": "yː",
        }

        # Check what follows
        remaining = text[pos + 1 :]

        # Special handling for 'e' - check for schwa
        if char == "e":
            # Word-final -e -> schwa
            if not remaining:
                return "ə"
            # -en, -el, -er at word end -> schwa
            if remaining in ("n", "l", "r", "m", "ns", "ln", "rn", "ls", "rs"):
                return "ə"
            # -end, -ent, -ens at word end (but not stressed like 'Trend')
            if remaining in ("nd", "nt", "ns") and pos > 0:
                return "ə"

        # Before 'h' + vowel or word end -> long
        if remaining.startswith("h") and (
            len(remaining) == 1 or remaining[1:2] in "aeiouäöü"
        ):
            return long_vowels.get(char, short_vowels.get(char, char))

        # Word-final vowel -> usually short except in some words
        if not remaining:
            return short_vowels.get(char, char)

        # Before single consonant at word end -> often long
        if len(remaining) == 1 and remaining[0] in "bcdfghjklmnpqrstvwxz":
            # Common pattern: V + single C at end = long vowel
            return long_vowels.get(char, short_vowels.get(char, char))

        # Before 'ch', 'ß' -> depends on word, often long
        if remaining.startswith(("ch", "ß")):
            return long_vowels.get(char, short_vowels.get(char, char))

        # Before single consonant + vowel (open syllable) -> long
        if (
            len(remaining) >= 2
            and remaining[0] in "bcdfghjklmnpqrstvwxz"
            and remaining[0] not in "ck"  # ck indicates short vowel
            and remaining[1] in "aeiouäöü"
            # But 'sch' is one sound, not cluster
            and not remaining.startswith("sch")
        ):
            return long_vowels.get(char, short_vowels.get(char, char))

        # Before consonant cluster -> short
        if (
            len(remaining) >= 2
            and remaining[0] in "bcdfghjklmnpqrstvwxz"
            and remaining[1] in "bcdfghjklmnpqrstvwxz"
        ):
            return short_vowels.get(char, char)

        # Default to short
        return short_vowels.get(char, char)

    def _apply_final_devoicing(self, phonemes: list[str]) -> list[str]:
        """Apply German final obstruent devoicing (Auslautverhärtung).

        Only applies to the final consonant cluster of the word.

        Args:
            phonemes: List of phoneme strings.

        Returns:
            Modified list with final devoicing applied.
        """
        if not phonemes:
            return phonemes

        vowels = frozenset(
            [
                "a",
                "aː",
                "e",
                "eː",
                "ɛ",
                "ɛː",
                "i",
                "iː",
                "ɪ",
                "o",
                "oː",
                "ɔ",
                "u",
                "uː",
                "ʊ",
                "y",
                "yː",
                "ʏ",
                "ø",
                "øː",
                "œ",
                "ə",
                "ɐ",
                "aɪ",
                "aʊ",
                "ɔʏ",
            ]
        )

        # Find the last consonant cluster (after the last vowel)
        last_vowel_idx = -1
        for i in range(len(phonemes) - 1, -1, -1):
            if phonemes[i] in vowels:
                last_vowel_idx = i
                break

        # Devoice all voiced obstruents after the last vowel
        for i in range(last_vowel_idx + 1, len(phonemes)):
            phone = phonemes[i]
            if phone in VOICED_TO_UNVOICED:
                phonemes[i] = VOICED_TO_UNVOICED[phone]

        return phonemes

    @staticmethod
    def _get_punct_phonemes(text: str) -> str:
        """Get phonemes for punctuation tokens.

        Only includes punctuation that exists in the Kokoro vocabulary.
        """
        # Punctuation marks that exist in Kokoro vocab
        # See kokorog2p/data/kokoro_config.json
        puncts = frozenset(';:,.!?"()')
        return "".join(c for c in text if c in puncts)

    def close(self) -> None:
        if self._lexicon is not None:
            self._lexicon.close()
        super().close()

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the dictionary.

        Args:
            word: The word to look up.
            The optional POS tag is forwarded to the source lexicon.

        Returns:
            Target-ready phoneme string if found and valid, None otherwise.
        """
        if self._lexicon is None:
            return None
        raw_phonemes = self._lexicon.lookup(word, tag)
        if raw_phonemes is None:
            return None
        return self._decode_lexicon_pronunciation(raw_phonemes)

    def phonemize(self, text: str) -> str:
        """Convert text to a phoneme string.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string.
        """
        tokens = self(text)
        return " ".join(t.phonemes or "" for t in tokens if t.phonemes)

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
