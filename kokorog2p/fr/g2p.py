"""French G2P (Grapheme-to-Phoneme) converter.

A Grapheme-to-Phoneme engine for French, designed for Kokoro TTS models.

Based on misaki French implementation, adapted for kokorog2p architecture.
"""

import re
import unicodedata

from kokorog2p.base import G2PBase
from kokorog2p.fr.fallback import FrenchFallback, FrenchGoruutFallback
from kokorog2p.fr.lexicon import FrenchLexicon, TokenContext
from kokorog2p.fr.normalizer import FrenchNormalizer
from kokorog2p.fr.numbers import expand_currency, expand_numbers, expand_time
from kokorog2p.token import GToken
from kokorog2p.tokenization import ensure_gtoken_positions


class FrenchG2P(G2PBase):
    """French G2P converter using dictionary lookup with fallback options.

    This class provides grapheme-to-phoneme conversion for French text,
    using a gold dictionary with espeak-ng or goruut as fallback for OOV words.

    Example:
        >>> g2p = FrenchG2P()
        >>> tokens = g2p("Bonjour, comment allez-vous?")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    # Punctuation normalization map
    _PUNCT_MAP = {
        chr(171): '"',  # «
        chr(187): '"',  # »
        chr(8216): "'",  # '
        chr(8217): "'",  # '
        chr(8220): '"',  # "
        chr(8221): '"',  # "
        chr(8212): "-",  # —
        chr(8211): "-",  # –
        chr(8230): "...",  # …
    }

    def __init__(
        self,
        language: str = "fr-fr",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_spacy: bool = True,
        expand_nums: bool = True,
        expand_abbreviations: bool = True,
        enable_context_detection: bool = True,
        unk: str = "?",
        load_silver: bool = True,
        load_gold: bool = True,
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the French G2P converter.

        Args:
            language: Language code (default: 'fr-fr').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            use_spacy: Whether to use spaCy for tokenization and POS tagging.
            expand_nums: Whether to expand numbers to words.
            expand_abbreviations: Whether to expand common abbreviations.
            enable_context_detection: Context-aware abbreviation expansion.
            unk: Character to use for unknown words when fallback is disabled.
            load_silver: If True, load silver tier dictionary if available.
                Currently French only has gold dictionary, so this parameter
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
        self.unk = unk
        self.use_spacy = use_spacy
        self.expand_nums = expand_nums

        # Initialize normalizer
        self._normalizer = FrenchNormalizer(
            expand_abbreviations=expand_abbreviations,
            enable_context_detection=enable_context_detection,
        )

        # Initialize lexicon
        self.lexicon = FrenchLexicon(load_silver=load_silver, load_gold=load_gold)

        # Initialize fallback (lazy)
        self._fallback: FrenchFallback | FrenchGoruutFallback | None = None

        # Initialize spaCy (lazy)
        self._nlp: object | None = None

    @property
    def fallback(self) -> FrenchFallback | FrenchGoruutFallback | None:
        """Lazily initialize the appropriate fallback."""
        if self._fallback is None:
            if self.use_goruut_fallback:
                self._fallback = FrenchGoruutFallback()
            elif self.use_espeak_fallback:
                self._fallback = FrenchFallback()
        return self._fallback

    @property
    def nlp(self) -> object:
        """Lazily initialize spaCy."""
        if self._nlp is None:
            import spacy

            name = "fr_core_news_sm"
            if not spacy.util.is_package(name):
                spacy.cli.download(name)  # type: ignore[attr-defined]
            self._nlp = spacy.load(name, enable=["tok2vec", "tagger"])
        return self._nlp

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        if not text.strip():
            return []

        # Preprocess
        text = self._preprocess(text)

        # Tokenize
        if self.use_spacy:
            tokens = self._tokenize_spacy(text)
        else:
            tokens = self._tokenize_simple(text)

        # Process tokens
        ctx = TokenContext()
        for token in tokens:
            # Skip tokens that already have phonemes (punctuation)
            if token.phonemes is not None:
                continue

            # Try lexicon lookup
            ps, rating = self.lexicon(token.text, token.tag, ctx)

            if ps is not None:
                token.phonemes = ps
                token.set("rating", rating)
            elif self.fallback is not None:
                # Try espeak fallback
                ps, rating = self.fallback(token.text)
                if ps is not None:
                    token.phonemes = ps
                    token.set("rating", rating)

        # Handle remaining unknown words
        for token in tokens:
            if token.phonemes is None and token.is_word:
                token.phonemes = self.unk

        ensure_gtoken_positions(tokens, text)
        return tokens

    def _preprocess(self, text: str) -> str:
        """Preprocess text before G2P conversion.

        Args:
            text: Raw input text.

        Returns:
            Preprocessed text.
        """
        # Normalize Unicode
        text = unicodedata.normalize("NFC", text)

        # Apply normalizer (abbreviations, temperature, etc.)
        text = self._normalizer(text)

        # Normalize punctuation (keep for legacy compatibility)
        for old, new in self._PUNCT_MAP.items():
            text = text.replace(old, new)

        # Remove non-breaking spaces
        text = text.replace("\u00a0", " ")
        text = text.replace("\u202f", " ")

        # Collapse multiple spaces
        text = re.sub(r" +", " ", text)

        # Expand abbreviations (legacy - now handled by normalizer)
        text = self.lexicon.expand_abbreviation(text)

        # Expand ordinals
        text = self.lexicon.expand_ordinals(text)

        # Expand time expressions
        text = expand_time(text)

        # Expand numbers
        if self.expand_nums:
            text = expand_numbers(text)

        # Expand currency
        text = expand_currency(text)

        return text.strip()

    def _tokenize_spacy(self, text: str) -> list[GToken]:
        """Tokenize text using spaCy.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        doc = self.nlp(text)  # type: ignore
        tokens: list[GToken] = []

        for tk in doc:
            token = GToken(
                text=tk.text,
                tag=tk.pos_,  # Use POS tag for French
                whitespace=tk.whitespace_,
            )

            # Handle punctuation
            if tk.pos_ == "PUNCT":
                token.phonemes = self._get_punct_phonemes(tk.text)
                token.set("rating", 4)

            tokens.append(token)

        return tokens

    def _tokenize_simple(self, text: str) -> list[GToken]:
        """Simple tokenization without spaCy.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        tokens: list[GToken] = []
        # Simple word/punct split
        for match in re.finditer(r"(\w+|[^\w\s]+|\s+)", text, re.UNICODE):
            word = match.group()
            if word.isspace():
                if tokens:
                    tokens[-1].whitespace = word
                continue

            token = GToken(text=word, tag="", whitespace="")

            # Handle punctuation
            if not any(c.isalnum() for c in word):
                token.phonemes = self._get_punct_phonemes(word)
                token.set("rating", 4)

            tokens.append(token)

        return tokens

    @staticmethod
    def _get_punct_phonemes(text: str) -> str:
        """Get phonemes for punctuation tokens."""
        # Keep common punctuation
        puncts = frozenset(";:,.!?-\"'()[]—…")
        return "".join("—" if c == "-" else c for c in text if c in puncts)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the dictionary.

        Args:
            word: The word to look up.
            tag: Optional POS tag for disambiguation.

        Returns:
            Phoneme string or None if not found.
        """
        ps, _ = self.lexicon(word, tag, None)
        return ps

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
