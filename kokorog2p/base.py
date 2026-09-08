"""Abstract base class for G2P (Grapheme-to-Phoneme) converters."""

from abc import ABC, abstractmethod
from typing import Literal

from .lexicons.evidence import LexiconEvidence
from .token import GToken

FallbackProvider = Literal["espeak", "goruut"] | None


def resolve_fallback_provider(
    *,
    use_espeak_fallback: bool,
    use_goruut_fallback: bool,
) -> FallbackProvider:
    if use_espeak_fallback and use_goruut_fallback:
        raise ValueError(
            "Cannot use both espeak and goruut fallback simultaneously. "
            "Please set only one of use_espeak_fallback or use_goruut_fallback to True."
        )
    if use_goruut_fallback:
        return "goruut"
    if use_espeak_fallback:
        return "espeak"
    return None

class G2PBase(ABC):
    """
    Abstract base class for grapheme-to-phoneme converters.

    Subclasses must implement the `__call__` method to convert text to phonemes.
    """

    def __init__(
        self,
        language: str = "en-us",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_cli: bool = False,
        strict: bool = True,
    ) -> None:
        """
        Initialize the G2P converter.

        Args:
            language: Language code (e.g., 'en-us', 'en-gb').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            use_cli: If True, use the CLI only for direct backend implementations.
            strict: If True, raise exceptions on errors. If False, log warnings
                and return empty results (backward compatible mode).
        """
        self.language = language
        self.use_espeak_fallback = use_espeak_fallback
        self.use_goruut_fallback = use_goruut_fallback
        self.fallback_provider = resolve_fallback_provider(
            use_espeak_fallback=use_espeak_fallback,
            use_goruut_fallback=use_goruut_fallback,
        )
        self.use_cli = use_cli
        self.strict = strict
        self.load_silver: bool | None = None
        self.load_gold: bool | None = None

    @property
    def is_british(self) -> bool:
        """Check if this is British English."""
        return self.language.lower() in ("en-gb", "en_gb", "british", "gb")

    @abstractmethod
    def __call__(self, text: str) -> list[GToken]:
        """
        Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        raise NotImplementedError

    def phonemize(self, text: str) -> str:
        """
        Convert text to a phoneme string.

        This is a convenience method that calls __call__ and joins the results.

        Args:
            text: Input text to convert.

        Returns:
            Phoneme string with word boundaries.
        """
        tokens = self(text)
        result: list[str] = []
        for token in tokens:
            if token.phonemes:
                result.append(token.phonemes)
                if token.whitespace:
                    result.append(token.whitespace)
            elif token.is_punctuation:
                # Keep punctuation as-is
                result.append(token.text)
                if token.whitespace:
                    result.append(token.whitespace)
        return "".join(result).strip()

    def word_to_phonemes(self, word: str, tag: str | None = None) -> str | None:
        """
        Convert a single word to phonemes.

        Args:
            word: The word to convert.
            tag: Optional POS tag for disambiguation.

        Returns:
            Phoneme string or None if conversion failed.
        """
        tokens = self(word)
        if tokens and tokens[0].phonemes:
            return tokens[0].phonemes
        return None

    @abstractmethod
    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """
        Look up a word in the dictionary.

        Args:
            word: The word to look up.
            tag: Optional POS tag for disambiguation.

        Returns:
            Phoneme string or None if not found.
        """
        raise NotImplementedError

    def lexicon_evidence(
        self, word: str, tag: str | None = None
    ) -> LexiconEvidence | None:
        """Return positive membership evidence from selected lexical resources."""
        return None

    def has_lexicon_evidence(self) -> bool:
        """Return whether this frontend can query a selected evidence resource."""
        selected = getattr(self, "lexicons", None)
        if selected is not None:
            return bool(selected)
        lexicon = getattr(self, "lexicon", None)
        selected = getattr(lexicon, "lexicons", None)
        if selected is not None:
            return bool(selected)
        return self.__class__.lexicon_evidence is not G2PBase.lexicon_evidence

    def close(self) -> None:
        """Release resources owned by this G2P instance."""
        return

    def __repr__(self) -> str:
        """Return a string representation."""
        return f"{self.__class__.__name__}(language={self.language!r})"
