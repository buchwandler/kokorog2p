"""English G2P (Grapheme-to-Phoneme) converter."""

from kokorog2p.base import G2PBase
from kokorog2p.en.fallback import EspeakFallback, GoruutFallback
from kokorog2p.en.lexicon import Lexicon, TokenContext
from kokorog2p.token import GToken


class EnglishG2P(G2PBase):
    """English G2P converter using dictionary lookup with fallback options.

    This class provides grapheme-to-phoneme conversion for English text,
    using a tiered dictionary system (gold/silver) with espeak-ng or goruut
    as fallback for out-of-vocabulary words.

    Example:
        >>> g2p = EnglishG2P(language="en-us")
        >>> tokens = g2p("Hello world!")
        >>> for token in tokens:
        ...     print(f"{token.text} -> {token.phonemes}")
    """

    def __init__(
        self,
        language: str = "en-us",
        use_espeak_fallback: bool = True,
        use_goruut_fallback: bool = False,
        use_spacy: bool = True,
        unk: str = "❓",
        load_silver: bool = True,
        load_gold: bool = True,
        version: str = "1.0",
        **kwargs,
    ) -> None:
        """Initialize the English G2P converter.

        Args:
            language: Language code ('en-us' or 'en-gb').
            use_espeak_fallback: Whether to use espeak for OOV words.
            use_goruut_fallback: Whether to use goruut for OOV words.
            use_spacy: Whether to use spaCy for tokenization and POS tagging.
            unk: Character to use for unknown words when fallback is disabled.
            load_silver: If True, load silver tier dictionary (~100k extra entries).
                Defaults to True for backward compatibility and maximum coverage.
                Set to False to save memory (~22-31 MB) and initialization time.
            load_gold: If True, load gold tier dictionary (~170k common words).
                Defaults to True for maximum quality and coverage.
                Set to False when only silver tier or no dictionaries needed.
            version: Model version ("1.1" for multilingual model, "1.0" for legacy).
                Defaults to "1.1".
            **kwargs: Additional arguments for future compatibility.

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

        super().__init__(language=language, use_espeak_fallback=use_espeak_fallback)

        self.version = version
        self.unk = unk
        self.use_spacy = use_spacy
        self.use_goruut_fallback = use_goruut_fallback

        # Initialize lexicon
        self.lexicon = Lexicon(
            british=self.is_british, load_silver=load_silver, load_gold=load_gold
        )

        # Initialize fallback (lazy)
        self._fallback: EspeakFallback | GoruutFallback | None = None

        # Initialize spaCy (lazy)
        self._nlp: object | None = None

    @property
    def fallback(self) -> EspeakFallback | GoruutFallback | None:
        """Lazily initialize the appropriate fallback."""
        if self._fallback is None:
            if self.use_goruut_fallback:
                self._fallback = GoruutFallback(british=self.is_british)
            elif self.use_espeak_fallback:
                self._fallback = EspeakFallback(british=self.is_british)
        return self._fallback

    @property
    def nlp(self) -> object:
        """Lazily initialize spaCy with custom tokenizer rules for contractions."""
        if self._nlp is None:
            import spacy

            name = "en_core_web_sm"
            if not spacy.util.is_package(name):
                spacy.cli.download(name)  # type: ignore[attr-defined]
            self._nlp = spacy.load(name, enable=["tok2vec", "tagger"])

            # Add tokenizer exceptions for contractions in our lexicon
            # This prevents spaCy from splitting contractions
            # like "don't" -> "do" + "n't"
            self._add_contraction_exceptions()

        return self._nlp

    def _add_contraction_exceptions(self) -> None:
        """Add tokenizer exceptions for contractions found in the lexicon.

        This tells spaCy to treat contractions as single tokens instead of
        splitting them, which allows us to look them up correctly in the lexicon.

        Uses the gold lexicon to identify words that:
        1. Contain apostrophes (formal contractions: don't, can't, etc.)
        2. Are informal contractions that spaCy tends to split (gonna, gotta, etc.)
        """
        # Get all words from lexicon that should be preserved as single tokens
        contractions = set()

        # Strategy 1: Add all words with apostrophes (formal contractions)
        # Include ALL words with apostrophes, regardless of phoneme quality
        for word in self.lexicon.golds.keys():
            if "'" in word:
                contractions.add(word)
                # Also add case variations
                contractions.add(word.capitalize())
                contractions.add(word.upper())

        if self.lexicon.silvers:
            for word in self.lexicon.silvers.keys():
                if "'" in word:
                    contractions.add(word)
                    contractions.add(word.capitalize())
                    contractions.add(word.upper())

        # Strategy 2: Add informal contractions from gold lexicon
        # Use a curated list of common informal contractions that spaCy splits
        # These are validated to exist in gold lexicon with good ratings
        informal_contractions = [
            "gonna",
            "wanna",
            "gotta",
            "kinda",
            "sorta",
            "outta",
            "lemme",
            "gimme",
            "dunno",
            "hafta",
            "woulda",
            "coulda",
            "shoulda",
            "musta",
            "oughta",
            "lotsa",
            "whaddya",
            "whatcha",
            "betcha",
            "gotcha",
            "wontcha",
            "dontcha",
            "didntcha",
        ]

        for word in informal_contractions:
            # Verify it exists in gold lexicon with good quality (rating 4)
            phoneme, rating = self.lexicon.lookup(word)
            if phoneme and rating == 4:
                contractions.add(word)
                contractions.add(word.capitalize())
                contractions.add(word.upper())

        # Strategy 3: Add common contraction patterns (for cases with poor
        # lexicon entries)
        # This catches cases like "should've", "would've" that may have
        # poor lexicon entries
        bases = ["should", "would", "could", "might", "must", "ought"]
        for base in bases:
            for suffix in ["'ve", "'d", "'ll", "n't"]:
                contractions.add(base + suffix)
                contractions.add(base.capitalize() + suffix)

        # Add special cases
        contractions.update(["y'all", "Y'all", "ain't", "Ain't"])

        # Add all identified words as spaCy tokenizer exceptions
        for contraction in contractions:
            # Normalize apostrophes before adding exception
            normalized = contraction.replace("\u2019", "'")
            normalized = normalized.replace("\u2018", "'")
            normalized = normalized.replace("`", "'")
            normalized = normalized.replace("\u00b4", "'")

            # Add as a special case (single token)
            self._nlp.tokenizer.add_special_case(normalized, [{"ORTH": normalized}])  # type: ignore

    def __call__(self, text: str) -> list[GToken]:
        """Convert text to a list of tokens with phonemes.

        Args:
            text: Input text to convert.

        Returns:
            List of GToken objects with phonemes assigned.
        """
        if not text.strip():
            return []

        # Tokenize
        if self.use_spacy:
            tokens = self._tokenize_spacy(text)
        else:
            tokens = self._tokenize_simple(text)

        # Process tokens in reverse order for context
        ctx = TokenContext()
        for i in range(len(tokens) - 1, -1, -1):
            token = tokens[i]

            # Skip tokens that already have phonemes (punctuation)
            if token.phonemes is not None:
                ctx = self._update_context(ctx, token.phonemes, token)
                continue

            # Try lexicon lookup
            ps, rating = self.lexicon(token.text, token.tag, None, ctx)

            if ps is not None:
                token.phonemes = ps
                token.set("rating", rating)
            elif self.fallback is not None:
                # Try espeak fallback
                ps, rating = self.fallback(token.text)
                if ps is not None:
                    token.phonemes = ps
                    token.set("rating", rating)

            # Update context
            ctx = self._update_context(ctx, token.phonemes, token)

        # Handle remaining unknown words
        for token in tokens:
            if token.phonemes is None:
                token.phonemes = self.unk

        return tokens

    def _tokenize_spacy(self, text: str) -> list[GToken]:
        """Tokenize text using spaCy with custom contraction handling.

        SpaCy is configured with tokenizer exceptions for all contractions
        in our lexicon, so they won't be split during tokenization.

        Args:
            text: Input text.

        Returns:
            List of GToken objects.
        """
        # Normalize apostrophes to standard straight apostrophe (U+0027)
        # This ensures tokenizer exceptions and lexicon lookups work correctly
        text = text.replace("\u2019", "'")  # Right single quotation mark
        text = text.replace("\u2018", "'")  # Left single quotation mark
        text = text.replace("`", "'")  # Grave accent
        text = text.replace("\u00b4", "'")  # Acute accent

        # Normalize ellipsis variants to single ellipsis character (U+2026)
        # This ensures consistent handling in vocab (ID 10)
        # Order matters: replace longer sequences first
        text = text.replace("....", "…")  # Four dots (typo variant)
        text = text.replace(". . .", "…")  # Spaced dots
        text = text.replace("...", "…")  # Three dots
        text = text.replace("..", "…")  # Two dots (typo variant)

        # Normalize dash variants to em dash (U+2014)
        # This ensures consistent handling in vocab (ID 9: " —")
        # Order matters: do space-surrounded replacements first
        text = text.replace(" - ", " — ")  # Spaced hyphen (used as em dash)
        text = text.replace(" -- ", " — ")  # Spaced double hyphen
        text = text.replace("--", "—")  # Double hyphen (common in typing)
        text = text.replace("\u2013", "—")  # En dash (–)
        text = text.replace("\u2015", "—")  # Horizontal bar (―)
        text = text.replace("\u2012", "—")  # Figure dash (‒)
        text = text.replace("\u2212", "—")  # Minus sign (−)
        # Note: Single hyphen (-) without spaces is kept for compound words

        # Use spaCy's tokenization (with our custom exceptions for contractions)
        doc = self.nlp(text)  # type: ignore

        # Convert to GToken objects
        tokens: list[GToken] = []

        for tk in doc:
            token = GToken(
                text=tk.text,
                tag=tk.tag_,
                whitespace=tk.whitespace_,
            )

            # Handle punctuation by tag OR by content
            # (for cases where spaCy mistagged)
            # Check if it's a punctuation tag OR if the text consists
            # only of punctuation
            is_punct_tag = tk.tag_ in (
                ".",
                ",",
                "-LRB-",
                "-RRB-",
                "``",
                '""',
                "''",
                ":",
                "$",
                "#",
                "NFP",
            )
            # Check if text is only punctuation/quotes (not alphanumeric)
            is_punct_text = tk.text and not any(c.isalnum() for c in tk.text)

            if is_punct_tag or is_punct_text:
                token.phonemes = self._get_punct_phonemes(tk.text, tk.tag_)
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
        import re

        # Normalize apostrophes to standard straight apostrophe (U+0027)
        text = text.replace("\u2019", "'")  # Right single quotation mark
        text = text.replace("\u2018", "'")  # Left single quotation mark
        text = text.replace("`", "'")  # Grave accent
        text = text.replace("\u00b4", "'")  # Acute accent

        tokens: list[GToken] = []
        # Tokenize with support for contractions (e.g., I've, we're, don't)
        # Pattern matches:
        # 1. Words with apostrophes (contractions): \w+'\w+
        # 2. Regular words: \w+
        # 3. Punctuation sequences: [^\w\s]+
        # 4. Whitespace: \s+
        for match in re.finditer(r"(\w+'\w+|\w+|[^\w\s]+|\s+)", text):
            word = match.group()
            if word.isspace():
                if tokens:
                    tokens[-1].whitespace = word
                continue

            token = GToken(text=word, tag="", whitespace="")

            # Handle punctuation (but not contractions with apostrophes)
            if not word.isalnum() and "'" not in word:
                token.phonemes = word if word in ".,;:!?-—…" else ""
                token.set("rating", 4)

            tokens.append(token)

        return tokens

    @staticmethod
    def _get_punct_phonemes(text: str, tag: str) -> str:
        """Get phonemes for punctuation tokens."""
        punct_map = {
            "-LRB-": "(",
            "-RRB-": ")",
            "``": chr(8220),  # Left double quote
            '""': chr(8221),  # Right double quote
            "''": chr(8221),  # Right double quote
        }
        if tag in punct_map:
            return punct_map[tag]

        # Keep common punctuation
        puncts = frozenset(';:,.!?—…"""')
        return "".join(c for c in text if c in puncts)

    def _update_context(
        self, ctx: TokenContext, phonemes: str | None, token: GToken
    ) -> TokenContext:
        """Update context based on processed token."""
        from kokorog2p.en.lexicon import CONSONANTS, VOWELS

        non_quote_puncts = frozenset(";:,.!?—…")

        future_vowel = ctx.future_vowel
        if phonemes:
            for c in phonemes:
                if c in VOWELS:
                    future_vowel = True
                    break
                elif c in CONSONANTS:
                    future_vowel = False
                    break
                elif c in non_quote_puncts:
                    future_vowel = None
                    break

        future_to = token.text.lower() in ("to",) and token.tag in ("TO", "IN", "")

        return TokenContext(future_vowel=future_vowel, future_to=future_to)

    def lookup(self, word: str, tag: str | None = None) -> str | None:
        """Look up a word in the dictionary.

        Args:
            word: The word to look up.
            tag: Optional POS tag for disambiguation.

        Returns:
            Phoneme string or None if not found.
        """
        ps, _ = self.lexicon(word, tag, None, None)
        return ps

    def __repr__(self) -> str:
        return f"EnglishG2P(language={self.language!r}, version={self.version!r})"

    def get_target_model(self) -> str:
        """Get the target Kokoro model variant for this G2P instance.

        Returns:
            Model identifier: version string ("1.1" or "1.0").
        """
        return self.version
